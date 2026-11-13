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

    # สร้างตาราง Wines (รองรับฟิลด์ 2 ภาษา _en)
    cursor.execute('''
        CREATE TABLE wines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            vintage TEXT,
            city TEXT,
            city_en TEXT,
            country TEXT,
            country_en TEXT,
            type TEXT,
            variety TEXT,
            alcohol REAL,
            size TEXT,
            brand TEXT,
            color TEXT,
            color_en TEXT,
            sweetness TEXT,
            sweetness_en TEXT,
            taste TEXT,
            taste_en TEXT,
            aroma TEXT,
            aroma_en TEXT,
            food_pairing TEXT,
            food_pairing_en TEXT,
            description TEXT,
            description_en TEXT,
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
    
    # อ่านไฟล์ CSV
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
        
        # ดึงข้อมูลภาษาไทยและอังกฤษ
        city = str(row.get('city', '')).strip()
        city_en = str(row.get('city_en', '')).strip() if pd.notna(row.get('city_en')) else ''
        country = str(row.get('country', '')).strip()
        country_en = str(row.get('country_en', '')).strip() if pd.notna(row.get('country_en')) else ''
        
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
        color_en = str(row.get('color_en', '')).strip() if pd.notna(row.get('color_en')) else ''
        
        sweetness = str(row.get('sweetness', '')).strip()
        sweetness_en = str(row.get('sweetness_en', '')).strip() if pd.notna(row.get('sweetness_en')) else ''
        
        taste = str(row.get('taste', '')).strip()
        taste_en = str(row.get('taste_en', '')).strip() if pd.notna(row.get('taste_en')) else ''
        
        aroma = str(row.get('aroma', '')).strip()
        aroma_en = str(row.get('aroma_en', '')).strip() if pd.notna(row.get('aroma_en')) else ''
        
        food_pairing = str(row.get('food_pairing', '')).strip()
        food_pairing_en = str(row.get('food_pairing_en', '')).strip() if pd.notna(row.get('food_pairing_en')) else ''
        
        description = str(row.get('description', '')).strip()
        description_en = str(row.get('description_en', '')).strip() if pd.notna(row.get('description_en')) else ''
        
        image_url = str(row.get('image_url', '')).strip()

        # ป้องกันกรณีสลับคอลัมน์ image_url กับ description
        if image_url.startswith('เป็นไวน์') or image_url.startswith('VRL') or len(image_url) > 150:
            temp = image_url
            image_url = description
            description = temp

        cursor.execute('''
            INSERT INTO wines (
                name, price, vintage, city, city_en, country, country_en, type, variety, 
                alcohol, size, brand, color, color_en, sweetness, sweetness_en, 
                taste, taste_en, aroma, aroma_en, food_pairing, food_pairing_en, 
                description, description_en, image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, price, vintage, city, city_en, country, country_en, wine_type, variety, 
            alcohol, size, brand, color, color_en, sweetness, sweetness_en, 
            taste, taste_en, aroma, aroma_en, food_pairing, food_pairing_en, 
            description, description_en, image_url
        ))
    
    # สร้างบัญชี Admin เริ่มต้น
    cursor.execute('''
        INSERT INTO users (first_name, last_name, email, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
    ''', ('Admin', 'System', 'admin@wine.com', generate_password_hash('admin123'), 'admin'))

    conn.commit()
    conn.close()
    print("Database reloaded successfully with dual-language support!")

if __name__ == '__main__':
    init_db()