import os, sqlite3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "nyikaroam_kenya.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'visitor', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS destinations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, county TEXT NOT NULL,
          category TEXT NOT NULL, description TEXT NOT NULL, animals TEXT NOT NULL,
          activities TEXT NOT NULL, best_time TEXT NOT NULL, budget_min INTEGER NOT NULL,
          budget_max INTEGER NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
          image_url TEXT NOT NULL, featured INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS saved_destinations(
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(user_id, destination_id)
        );
        CREATE TABLE IF NOT EXISTS searches(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
          interests TEXT NOT NULL, budget INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS feedback(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
          destination_id INTEGER REFERENCES destinations(id) ON DELETE SET NULL,
          rating INTEGER NOT NULL, comment TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
        if count == 0:
            seed = [
            ("Maasai Mara National Reserve","Narok","Wildlife","Iconic open savannah, seasonal wildebeest migration and rich wildlife viewing.","lion, elephant, leopard, cheetah, wildebeest, zebra","game drives, photography, cultural visits","July–October; wildlife viewing year-round",18000,65000,-1.493,35.143,"https://images.unsplash.com/photo-1516026672322-bc52d61a55d5",1),
            ("Amboseli National Park","Kajiado","Wildlife","Known for large elephant herds and wide views towards Mount Kilimanjaro.","elephant, lion, buffalo, giraffe, zebra","game drives, birdwatching, photography","June–October; January–February",14000,52000,-2.652,37.260,"https://images.unsplash.com/photo-1516026672322-bc52d61a55d5",1),
            ("Lake Nakuru National Park","Nakuru","Nature & Wildlife","A scenic Rift Valley lake ecosystem with rhinos, diverse birds and woodland.","rhino, giraffe, buffalo, flamingo, pelican","birdwatching, game drives, hiking viewpoints","June–March",10000,38000,-0.367,36.083,"https://images.unsplash.com/photo-1547471080-7cc2caa01a7e",1),
            ("Samburu National Reserve","Samburu","Wildlife","A semi-arid northern landscape with distinctive wildlife and the Ewaso Ng'iro River.","grevy zebra, reticulated giraffe, gerenuk, elephant, lion","game drives, birdwatching, cultural experiences","June–October; December–March",16000,50000,0.566,37.535,"https://images.unsplash.com/photo-1535338454770-8be927b5a00b",1),
            ("Tsavo East National Park","Taita-Taveta","Wildlife","Vast open wilderness, red-dust elephants and the Galana River landscape.","elephant, lion, giraffe, zebra, buffalo","game drives, photography, nature viewing","June–October; January–February",9000,35000,-3.071,38.776,"https://images.unsplash.com/photo-1511497584788-876760111969",0),
            ("Ol Pejeta Conservancy","Laikipia","Conservancy","A conservation landscape known for rhino protection and community-led conservation.","black rhino, white rhino, elephant, lion, chimpanzee","game drives, conservation visits, guided walks","June–September; December–February",15000,48000,0.000,36.967,"https://images.unsplash.com/photo-1509316785289-025f5b846b35",0),
            ("Diani Beach","Kwale","Beach","A tropical Indian Ocean coastline with white sand, coral reefs and water activities.","dolphin, sea turtle, reef fish","snorkelling, diving, kitesurfing, relaxation","July–October; December–March",8000,40000,-4.279,39.594,"https://images.unsplash.com/photo-1500375592092-40eb2168fd21",1),
            ("Lamu Old Town","Lamu","Culture & Heritage","A historic Swahili coastal town with narrow lanes, carved doors and dhow culture.","dolphin, sea turtle, coastal birds","heritage walks, dhow trips, cultural experiences","July–October; January–March",7000,30000,-2.271,40.902,"https://images.unsplash.com/photo-1519046904884-53103b34b206",0)
            ]
            db.executemany("""INSERT INTO destinations
            (name,county,category,description,animals,activities,best_time,budget_min,budget_max,latitude,longitude,image_url,featured)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", seed)
