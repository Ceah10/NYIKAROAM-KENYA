import sys
from .database import init_db, connect

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m app.make_admin email@example.com"); return
    init_db()
    email=sys.argv[1].strip().lower()
    with connect() as db:
        cur=db.execute("UPDATE users SET role='admin' WHERE email=?",(email,))
        if cur.rowcount: print(f"{email} is now an administrator.")
        else: print("No account found. Register this email in the website first.")
if __name__ == "__main__": main()
