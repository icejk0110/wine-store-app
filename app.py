import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_wine'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

# API: สมัครสมาชิก
@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if user:
        conn.close()
        return jsonify({'success': False, 'message': 'อีเมลนี้ถูกใช้งาน, กรุณาใช้อีเมลอื่น'})

    hashed_pw = generate_password_hash(password)
    conn.execute('INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)',
                 (first_name, last_name, email, hashed_pw, 'customer'))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'สมัครสมาชิกสำเร็จ'})

# API: เข้าสู่ระบบ
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['role'] = user['role']
        session['name'] = f"{user['first_name']} {user['last_name']}"
        return jsonify({'success': True, 'role': user['role'], 'name': session['name']})
    
    return jsonify({'success': False, 'message': 'อีเมลหรือรหัสผ่านไม่ถูกต้อง'})

# API: ออกจากระบบ
@app.route('/api/logout')
def api_logout():
    session.clear()
    return jsonify({'success': True})

# API: ดึงรายการไวน์ พร้อมตัวกรอง (Filters)
@app.route('/api/wines', methods=['GET'])
def api_wines():
    price_range = request.args.get('price')
    wine_type = request.args.get('type')
    vintage = request.args.get('vintage')
    country = request.args.get('country')
    brand = request.args.get('brand')

    query = "SELECT * FROM wines WHERE 1=1"
    params = []

    if price_range:
        if price_range == 'ต่ำกว่า 599':
            query += " AND price < 599"
        elif price_range == '4900 ขึ้นไป':
            query += " AND price >= 4900"
        else:
            parts = price_range.split(' – ')
            if len(parts) == 2:
                query += " AND price BETWEEN ? AND ?"
                params.extend([float(parts[0]), float(parts[1])])

    if wine_type:
        query += " AND type = ?"
        params.append(wine_type)

    if vintage:
        if vintage == '2015 – 2018':
            query += " AND vintage IN ('2015', '2016', '2017', '2018')"
        elif vintage == '2019 – 2022':
            query += " AND vintage IN ('2019', '2020', '2021', '2022')"
        elif vintage == '2023 – 2026':
            query += " AND vintage IN ('2023', '2024', '2025', '2026')"

    if country:
        query += " AND country = ?"
        params.append(country)

    if brand:
        query += " AND brand = ?"
        params.append(brand)

    conn = get_db_connection()
    wines = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(w) for w in wines])

# API: บันทึกความสนใจไวน์
@app.route('/api/interest', methods=['POST'])
def api_interest():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'กรุณาเข้าสู่ระบบก่อน'})
    
    data = request.json
    user_id = session['user_id']
    wine_id = data.get('wine_id')
    quantity = data.get('quantity', 1)

    conn = get_db_connection()
    conn.execute('INSERT INTO customer_interests (user_id, wine_id, quantity, status) VALUES (?, ?, ?, ?)',
                 (user_id, wine_id, quantity, 'กำลังจัดสั่งซื้อ'))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'บันทึกรายการความสนใจสำเร็จ'})

# API: ดึงรายการที่บันทึกของลูกค้า หรือ Admin ดูทั้งหมด
@app.route('/api/interests/list', methods=['GET'])
def api_interests_list():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})

    conn = get_db_connection()
    if session['role'] == 'admin':
        rows = conn.execute('''
            SELECT ci.*, w.name as wine_name, w.price, w.image_url, u.first_name, u.last_name, u.email 
            FROM customer_interests ci
            JOIN wines w ON ci.wine_id = w.id
            JOIN users u ON ci.user_id = u.id
            ORDER BY ci.created_at DESC
        ''').fetchall()
    else:
        rows = conn.execute('''
            SELECT ci.*, w.name as wine_name, w.price, w.image_url 
            FROM customer_interests ci
            JOIN wines w ON ci.wine_id = w.id
            WHERE ci.user_id = ?
            ORDER BY ci.created_at DESC
        ''', (session['user_id'],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# API: Admin อัพเดตสถานะไวน์
@app.route('/api/admin/update-status', methods=['POST'])
def update_status():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    data = request.json
    interest_id = data.get('interest_id')
    new_status = data.get('status')

    conn = get_db_connection()
    conn.execute('UPDATE customer_interests SET status = ? WHERE id = ?', (new_status, interest_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# API: Admin จัดการไวน์ (Add / Delete)
@app.route('/api/admin/wine', methods=['POST', 'DELETE'])
def admin_wine_manage():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'})

    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute('''
            INSERT INTO wines (name, price, vintage, city, country, type, variety, alcohol, size, brand, color, sweetness, taste, aroma, food_pairing, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'), data.get('price'), data.get('vintage'), data.get('city'), data.get('country'),
            data.get('type'), data.get('variety'), data.get('alcohol'), data.get('size'), data.get('brand'),
            data.get('color'), data.get('sweetness'), data.get('taste'), data.get('aroma'),
            data.get('food_pairing'), data.get('description'), data.get('image_url')
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'เพิ่มไวน์สำเร็จ'})
    
    elif request.method == 'DELETE':
        wine_id = request.args.get('id')
        conn.execute('DELETE FROM wines WHERE id = ?', (wine_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'ลบไวน์สำเร็จ'})

# API: รายงานการใช้งานระบบ (รายวัน, รายเดือน, รายปี)
@app.route('/api/admin/reports', methods=['GET'])
def admin_reports():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    period = request.args.get('period', 'monthly')
    conn = get_db_connection()
    
    if period == 'daily':
        group_format = "%Y-%m-%d"
    elif period == 'yearly':
        group_format = "%Y"
    else:
        group_format = "%Y-%m"

    query = f'''
        strftime('{group_format}', created_at) as period_time,
        COUNT(*) as total_requests,
        SUM(quantity) as total_quantity
        FROM customer_interests
        GROUP BY period_time
        ORDER BY period_time DESC
    '''
    rows = conn.execute(f"SELECT {query}").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
# เพิ่ม API สำหรับ Social Login ใน app.py
@app.route('/api/social-login', methods=['POST'])
def api_social_login():
    data = request.json
    provider = data.get('provider')
    email = f"user@{provider.lower()}.com"
    name = f"{provider} User"

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    if not user:
        # ถ้ายังไม่มีบัญชี Social นี้ ให้สร้างให้อัตโนมัติ
        conn.execute('INSERT INTO users (first_name, last_name, email, password_hash, role, oauth_provider) VALUES (?, ?, ?, ?, ?, ?)',
                     (provider, 'User', email, generate_password_hash('social_secure'), 'customer', provider))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    session['user_id'] = user['id']
    session['email'] = user['email']
    session['role'] = user['role']
    session['name'] = f"{user['first_name']} {user['last_name']}"
    conn.close()

    return jsonify({'success': True, 'role': user['role'], 'name': session['name']})

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)