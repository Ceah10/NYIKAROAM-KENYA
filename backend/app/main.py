from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from .database import connect, init_db
from .schemas import RegisterIn, LoginIn, RecommendIn, FeedbackIn, DestinationIn
from .security import hash_password, verify_password, create_token, decode_token
import os, json

app = FastAPI(title="Nyikaroam Kenya API", version="1.0.0",
              description="Personalised discovery for travel across Kenya.")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): init_db()

def rowdict(row):
    d = dict(row)
    for key in ("animals", "activities"):
        if key in d: d[key] = [x.strip() for x in d[key].split(",") if x.strip()]
    if "featured" in d: d["featured"] = bool(d["featured"])
    return d

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "): return None
    uid = decode_token(authorization[7:])
    if not uid: return None
    with connect() as db: user = db.execute("SELECT id,name,email,role FROM users WHERE id=?", (uid,)).fetchone()
    return dict(user) if user else None

def require_user(user=Depends(current_user)):
    if not user: raise HTTPException(401, "Please sign in to continue.")
    return user

def require_admin(user=Depends(require_user)):
    if user["role"] != "admin": raise HTTPException(403, "Administrator access required.")
    return user

@app.get("/")
def home(): return {"name":"Nyikaroam Kenya API","status":"running","docs":"/docs"}

@app.get("/api/health")
def health(): return {"status":"healthy"}

@app.post("/api/auth/register")
def register(data: RegisterIn):
    email = data.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]: raise HTTPException(422, "Enter a valid email address.")
    with connect() as db:
        try:
            cur = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                             (data.name.strip(), email, hash_password(data.password)))
            uid = cur.lastrowid
        except Exception: raise HTTPException(409, "An account with this email already exists.")
    user = {"id":uid,"name":data.name.strip(),"email":email,"role":"visitor"}
    return {"token":create_token(uid),"user":user}

@app.post("/api/auth/login")
def login(data: LoginIn):
    with connect() as db: row = db.execute("SELECT * FROM users WHERE email=?", (data.email.strip().lower(),)).fetchone()
    if not row or not verify_password(data.password, row["password_hash"]): raise HTTPException(401, "Email or password is incorrect.")
    user = {"id":row["id"],"name":row["name"],"email":row["email"],"role":row["role"]}
    return {"token":create_token(row["id"]),"user":user}

@app.get("/api/auth/me")
def me(user=Depends(require_user)): return user

@app.get("/api/destinations")
def destinations(search: str = "", category: str = "All", county: str = "All"):
    sql = "SELECT * FROM destinations WHERE 1=1"; args=[]
    if search:
        sql += " AND (name LIKE ? OR county LIKE ? OR description LIKE ?)"; args += [f"%{search}%"]*3
    if category != "All": sql += " AND category=?"; args.append(category)
    if county != "All": sql += " AND county=?"; args.append(county)
    sql += " ORDER BY featured DESC,name"
    with connect() as db: rows=db.execute(sql,args).fetchall()
    return [rowdict(r) for r in rows]

@app.get("/api/destinations/{destination_id}")
def destination_detail(destination_id: int):
    with connect() as db: row=db.execute("SELECT * FROM destinations WHERE id=?", (destination_id,)).fetchone()
    if not row: raise HTTPException(404,"Destination not found.")
    return rowdict(row)

@app.post("/api/recommend")
def recommend(data: RecommendIn, user=Depends(current_user)):
    interests = [x.lower() for x in data.interests]
    with connect() as db:
        rows=db.execute("SELECT * FROM destinations").fetchall()
        db.execute("INSERT INTO searches(user_id,interests,budget) VALUES(?,?,?)",
                   (user["id"] if user else None, ",".join(data.interests), data.budget))
    ranked=[]
    for r in rows:
        d=rowdict(r); hay=" ".join([d["category"],d["county"],d["description"],*d["animals"],*d["activities"]]).lower()
        matched=[x for x in interests if x in hay]
        score=len(matched)*3
        if data.budget >= d["budget_min"]: score += 2
        if data.budget >= d["budget_max"]: score += 1
        if data.county != "Any" and data.county.lower()==d["county"].lower(): score += 3
        if data.travel_style != "Any" and data.travel_style.lower() in hay: score += 1
        d["match_score"]=score
        d["reasons"] = (["Matches your interests: "+", ".join(matched)] if matched else ["A popular place to explore"])
        d["reasons"].append("Estimated budget range: KES {:,}–{:,}".format(d["budget_min"],d["budget_max"]))
        ranked.append(d)
    ranked.sort(key=lambda x:(x["match_score"],x["featured"]),reverse=True)
    return ranked[:6]

@app.get("/api/saved")
def saved(user=Depends(require_user)):
    with connect() as db:
        rows=db.execute("""SELECT d.* FROM destinations d JOIN saved_destinations s
        ON s.destination_id=d.id WHERE s.user_id=? ORDER BY s.created_at DESC""",(user["id"],)).fetchall()
    return [rowdict(r) for r in rows]

@app.post("/api/saved/{destination_id}")
def toggle_saved(destination_id: int, user=Depends(require_user)):
    with connect() as db:
        exists=db.execute("SELECT 1 FROM saved_destinations WHERE user_id=? AND destination_id=?",(user["id"],destination_id)).fetchone()
        if exists:
            db.execute("DELETE FROM saved_destinations WHERE user_id=? AND destination_id=?",(user["id"],destination_id))
            return {"saved":False}
        if not db.execute("SELECT 1 FROM destinations WHERE id=?",(destination_id,)).fetchone(): raise HTTPException(404,"Destination not found.")
        db.execute("INSERT INTO saved_destinations(user_id,destination_id) VALUES(?,?)",(user["id"],destination_id))
    return {"saved":True}

@app.get("/api/history")
def history(user=Depends(require_user)):
    with connect() as db:
        rows=db.execute("SELECT interests,budget,created_at FROM searches WHERE user_id=? ORDER BY id DESC LIMIT 20",(user["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/feedback")
def feedback(data: FeedbackIn, user=Depends(require_user)):
    with connect() as db:
        if not db.execute("SELECT 1 FROM destinations WHERE id=?",(data.destination_id,)).fetchone(): raise HTTPException(404,"Destination not found.")
        db.execute("INSERT INTO feedback(user_id,destination_id,rating,comment) VALUES(?,?,?,?)",
                   (user["id"],data.destination_id,data.rating,data.comment))
    return {"message":"Thank you for your feedback."}

@app.get("/api/admin/stats")
def admin_stats(user=Depends(require_admin)):
    with connect() as db:
        return {"users":db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "destinations":db.execute("SELECT COUNT(*) FROM destinations").fetchone()[0],
                "searches":db.execute("SELECT COUNT(*) FROM searches").fetchone()[0],
                "feedback":db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]}

@app.post("/api/admin/destinations")
def create_destination(data: DestinationIn, user=Depends(require_admin)):
    with connect() as db:
        cur=db.execute("""INSERT INTO destinations(name,county,category,description,animals,activities,best_time,
        budget_min,budget_max,latitude,longitude,image_url,featured) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.name,data.county,data.category,data.description,data.animals,data.activities,data.best_time,
         data.budget_min,data.budget_max,data.latitude,data.longitude,data.image_url,int(data.featured)))
    return {"id":cur.lastrowid,"message":"Destination created."}

@app.put("/api/admin/destinations/{destination_id}")
def update_destination(destination_id: int, data: DestinationIn, user=Depends(require_admin)):
    with connect() as db:
        cur=db.execute("""UPDATE destinations SET name=?,county=?,category=?,description=?,animals=?,activities=?,best_time=?,
        budget_min=?,budget_max=?,latitude=?,longitude=?,image_url=?,featured=? WHERE id=?""",
        (data.name,data.county,data.category,data.description,data.animals,data.activities,data.best_time,
         data.budget_min,data.budget_max,data.latitude,data.longitude,data.image_url,int(data.featured),destination_id))
        if cur.rowcount==0: raise HTTPException(404,"Destination not found.")
    return {"message":"Destination updated."}

@app.delete("/api/admin/destinations/{destination_id}")
def delete_destination(destination_id: int, user=Depends(require_admin)):
    with connect() as db:
        cur=db.execute("DELETE FROM destinations WHERE id=?",(destination_id,))
        if cur.rowcount==0: raise HTTPException(404,"Destination not found.")
    return {"message":"Destination deleted."}
