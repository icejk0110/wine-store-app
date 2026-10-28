import sqlite3
import pandas as pd
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # ลบตารางเดิมเพื่อสร้างใหม่
    cursor.execute('DROP TABLE IF EXISTS wines')
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS customer_interests')

    # สร้างตาราง Users
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'customer',
            oauth_provider TEXT
        )
    ''')

    # สร้างตาราง Wines
    cursor.execute('''
        CREATE TABLE wines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            vintage TEXT,
            city TEXT,
            country TEXT,
            type TEXT,
            variety TEXT,
            alcohol REAL,
            size TEXT,
            brand TEXT,
            color TEXT,
            sweetness TEXT,
            taste TEXT,
            aroma TEXT,
            food_pairing TEXT,
            description TEXT,
            image_url TEXT
        )
    ''')

    # สร้างตาราง CustomerInterests
    cursor.execute('''
        CREATE TABLE customer_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wine_id INTEGER,
            quantity INTEGER,
            status TEXT DEFAULT 'กำลังจัดสั่งซื้อ',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(wine_id) REFERENCES wines(id)
        )
    ''')

    conn.commit()
    
    # อ่านไฟล์ CSV โดยระบุ quoting และ on_bad_lines ป้องกันข้อมูลเลื่อม
    try:
        df = pd.read_csv('wines_new_2.csv', encoding='utf-8', on_bad_lines='skip')
    except Exception as e:
        df = pd.read_csv('wines_new_2.csv', encoding='latin1', on_bad_lines='skip')

    df.columns = df.columns.str.strip()
    
    for _, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        if not name or name == 'nan':
            continue  # ข้ามแถวที่ไม่มีชื่อไวน์

        # ตรวจสอบราคา
        try:
            price = float(str(row.get('price', 0)).replace(',', '').strip())
        except:
            price = 0.0

        vintage = str(row.get('vintage', '')).strip()
        city = str(row.get('city', '')).strip()
        country = str(row.get('country', '')).strip()
        wine_type = str(row.get('type', '')).strip()
        variety = str(row.get('variety', '')).strip()
        
        # จัดการแอลกอฮอล์
        try:
            alc_raw = str(row.get('alcohol', 0)).replace('%', '').strip()
            alcohol = float(alc_raw)
            if alcohol > 1: 
                alcohol = alcohol / 100.0
        except:
            alcohol = 0.0

        size = str(row.get('size', '')).strip()
        brand = str(row.get('brand', '')).strip()
        color = str(row.get('color', '')).strip()
        sweetness = str(row.get('sweetness', '')).strip()
        taste = str(row.get('taste', '')).strip()
        aroma = str(row.get('aroma', '')).strip()
        food_pairing = str(row.get('food_pairing', '')).strip()
        description = str(row.get('description', '')).strip()
        image_url = str(row.get('image_url', '')).strip()

        # ป้องกันกรณีสลับคอลัมน์ image_url กับ description
        if image_url.startswith('เป็นไวน์') or image_url.startswith('VRL') or len(image_url) > 150:
            # สลับกลับหากข้อมูลสลับกัน
            temp = image_url
            image_url = description
            description = temp

        cursor.execute('''
            INSERT INTO wines (name, price, vintage, city, country, type, variety, alcohol, size, brand, color, sweetness, taste, aroma, food_pairing, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, price, vintage, city, country, wine_type, variety, alcohol, size, 
            brand, color, sweetness, taste, aroma, food_pairing, description, image_url
        ))
    
    # สร้างบัญชี Admin เริ่มต้น
    cursor.execute('''
        INSERT INTO users (first_name, last_name, email, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Admin', 'System', 'admin@wine.com', generate_password_hash('admin123'), 'admin'))

    conn.commit()
    conn.close()
    print("Database reloaded successfully with fixed column alignment!")

if __name__ == '__main__':
    init_db()