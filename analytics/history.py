import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            btc_price REAL,
            max_pain REAL,
            call_wall REAL,
            put_wall REAL,
            pcr REAL,
            nearest_exp TEXT,
            nearest_dte REAL
        )
    """)
    conn.commit()
    conn.close()

def save_snapshot(btc_price: float, max_pain: float, call_wall: float, put_wall: float, pcr: float, nearest_exp: str, nearest_dte: float):
    if btc_price == 0:
        return

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Проверка: не записывать дубликат, если с последнего снимка прошло меньше 15 минут
    cursor.execute("SELECT timestamp FROM snapshots ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    
    now = datetime.utcnow()
    if last_row:
        last_time = datetime.strptime(last_row[0], "%Y-%m-%d %H:%M:%S")
        if (now - last_time).total_seconds() < 900:  # 15 минут
            conn.close()
            return

    cursor.execute("""
        INSERT INTO snapshots (timestamp, btc_price, max_pain, call_wall, put_wall, pcr, nearest_exp, nearest_dte)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (now.strftime("%Y-%m-%d %H:%M:%S"), btc_price, max_pain, call_wall, put_wall, pcr, nearest_exp, nearest_dte))
    
    conn.commit()
    conn.close()

def get_history_df() -> pd.DataFrame:
    init_db()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY timestamp DESC", conn)
    conn.close()
    return df