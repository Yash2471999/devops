from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Database initialization
def init_db():
    conn = sqlite3.connect('hotel.db')
    cursor = conn.cursor()
    
    # Rooms table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'available'
        )
    ''')
    
    # Guests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT
        )
    ''')
    
    # Bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER,
            room_id INTEGER,
            check_in DATE NOT NULL,
            check_out DATE NOT NULL,
            total_amount REAL,
            status TEXT DEFAULT 'confirmed',
            FOREIGN KEY (guest_id) REFERENCES guests (id),
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')
    
    # Staff table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def get_db_connection():
    conn = sqlite3.connect('hotel.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_staff(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Room Management Routes
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()
    
    return jsonify([dict(room) for room in rooms])

@app.route('/api/rooms', methods=['POST'])
@authenticate_staff
def add_room():
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO rooms (room_number, room_type, price) VALUES (?, ?, ?)',
            (data['room_number'], data['room_type'], data['price'])
        )
        conn.commit()
        return jsonify({'message': 'Room added successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Room number already exists'}), 400
    finally:
        conn.close()

@app.route('/api/rooms/<int:room_id>', methods=['PUT'])
@authenticate_staff
def update_room(room_id):
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute(
        'UPDATE rooms SET room_type=?, price=?, status=? WHERE id=?',
        (data.get('room_type'), data.get('price'), data.get('status'), room_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Room updated successfully'})

# Guest Management Routes
@app.route('/api/guests', methods=['POST'])
def register_guest():
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO guests (name, email, phone, address) VALUES (?, ?, ?, ?)',
            (data['name'], data['email'], data['phone'], data.get('address', ''))
        )
        guest_id = cursor.lastrowid
        conn.commit()
        return jsonify({'message': 'Guest registered successfully', 'guest_id': guest_id}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/guests/<int:guest_id>', methods=['GET'])
def get_guest(guest_id):
    conn = get_db_connection()
    guest = conn.execute('SELECT * FROM guests WHERE id = ?', (guest_id,)).fetchone()
    conn.close()
    
    if guest:
        return jsonify(dict(guest))
    return jsonify({'error': 'Guest not found'}), 404

# Booking Management Routes
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    
    conn = get_db_connection()
    
    # Check room availability
    existing_booking = conn.execute('''
        SELECT id FROM bookings 
        WHERE room_id = ? AND status = 'confirmed'
        AND ((check_in <= ? AND check_out > ?) OR (check_in < ? AND check_out >= ?))
    ''', (data['room_id'], data['check_in'], data['check_in'], 
          data['check_out'], data['check_out'])).fetchone()
    
    if existing_booking:
        conn.close()
        return jsonify({'error': 'Room not available for selected dates'}), 400
    
    # Get room price
    room = conn.execute('SELECT price FROM rooms WHERE id = ?', (data['room_id'],)).fetchone()
    
    # Calculate total amount
    check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
    check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
    nights = (check_out - check_in).days
    total_amount = nights * room['price']
    
    # Create booking
    cursor = conn.execute('''
        INSERT INTO bookings (guest_id, room_id, check_in, check_out, total_amount)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['guest_id'], data['room_id'], data['check_in'], 
          data['check_out'], total_amount))
    
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': 'Booking created successfully',
        'booking_id': booking_id,
        'total_amount': total_amount
    }), 201

@app.route('/api/bookings', methods=['GET'])
@authenticate_staff
def get_bookings():
    conn = get_db_connection()
    bookings = conn.execute('''
        SELECT b.*, g.name as guest_name, r.room_number 
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.check_in DESC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(booking) for booking in bookings])

@app.route('/api/bookings/<int:booking_id>', methods=['PUT'])
@authenticate_staff
def update_booking(booking_id):
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute(
        'UPDATE bookings SET status = ? WHERE id = ?',
        (data['status'], booking_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Booking updated successfully'})

# Check-in/Check-out Routes
@app.route('/api/checkin/<int:booking_id>', methods=['POST'])
@authenticate_staff
def checkin(booking_id):
    conn = get_db_connection()
    
    # Update booking status
    conn.execute(
        'UPDATE bookings SET status = ? WHERE id = ?',
        ('checked_in', booking_id)
    )
    
    # Update room status
    booking = conn.execute(
        'SELECT room_id FROM bookings WHERE id = ?', (booking_id,)
    ).fetchone()
    
    conn.execute(
        'UPDATE rooms SET status = ? WHERE id = ?',
        ('occupied', booking['room_id'])
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Check-in completed successfully'})

@app.route('/api/checkout/<int:booking_id>', methods=['POST'])
@authenticate_staff
def checkout(booking_id):
    conn = get_db_connection()
    
    # Update booking status
    conn.execute(
        'UPDATE bookings SET status = ? WHERE id = ?',
        ('checked_out', booking_id)
    )
    
    # Update room status
    booking = conn.execute(
        'SELECT room_id FROM bookings WHERE id = ?', (booking_id,)
    ).fetchone()
    
    conn.execute(
        'UPDATE rooms SET status = ? WHERE id = ?',
        ('available', booking['room_id'])
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Check-out completed successfully'})

# Staff Authentication Routes
@app.route('/api/staff/login', methods=['POST'])
def staff_login():
    data = request.get_json()
    
    conn = get_db_connection()
    staff = conn.execute(
        'SELECT * FROM staff WHERE username = ? AND password = ?',
        (data['username'], hash_password(data['password']))
    ).fetchone()
    conn.close()
    
    if staff:
        return jsonify({
            'message': 'Login successful',
            'staff_id': staff['id'],
            'role': staff['role'],
            'name': staff['name']
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/staff/register', methods=['POST'])
def register_staff():
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO staff (username, password, role, name) VALUES (?, ?, ?, ?)',
            (data['username'], hash_password(data['password']), 
             data['role'], data['name'])
        )
        conn.commit()
        return jsonify({'message': 'Staff registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

# Dashboard/Reports Routes
@app.route('/api/dashboard/stats', methods=['GET'])
@authenticate_staff
def get_dashboard_stats():
    conn = get_db_connection()
    
    # Get room statistics
    total_rooms = conn.execute('SELECT COUNT(*) as count FROM rooms').fetchone()['count']
    occupied_rooms = conn.execute(
        'SELECT COUNT(*) as count FROM rooms WHERE status = "occupied"'
    ).fetchone()['count']
    
    # Get booking statistics
    today = datetime.now().strftime('%Y-%m-%d')
    todays_checkins = conn.execute(
        'SELECT COUNT(*) as count FROM bookings WHERE check_in = ? AND status = "confirmed"',
        (today,)
    ).fetchone()['count']
    
    todays_checkouts = conn.execute(
        'SELECT COUNT(*) as count FROM bookings WHERE check_out = ? AND status = "checked_in"',
        (today,)
    ).fetchone()['count']
    
    # Revenue for current month
    current_month = datetime.now().strftime('%Y-%m')
    monthly_revenue = conn.execute(
        'SELECT SUM(total_amount) as revenue FROM bookings WHERE substr(check_in, 1, 7) = ?',
        (current_month,)
    ).fetchone()['revenue'] or 0
    
    conn.close()
    
    return jsonify({
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_rooms,
        'available_rooms': total_rooms - occupied_rooms,
        'todays_checkins': todays_checkins,
        'todays_checkouts': todays_checkouts,
        'monthly_revenue': monthly_revenue
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Initialize database and run the application
if __name__ == '__main__':
    init_db()
    
    # Add some sample data for testing
    conn = get_db_connection()
    
    # Sample rooms
    try:
        conn.execute('INSERT INTO rooms (room_number, room_type, price) VALUES ("101", "Single", 100.0)')
        conn.execute('INSERT INTO rooms (room_number, room_type, price) VALUES ("102", "Double", 150.0)')
        conn.execute('INSERT INTO rooms (room_number, room_type, price) VALUES ("201", "Suite", 300.0)')
        
        # Sample staff
        conn.execute('INSERT INTO staff (username, password, role, name) VALUES ("admin", ?, "manager", "Hotel Manager")', 
                    (hash_password("admin123"),))
        conn.execute('INSERT INTO staff (username, password, role, name) VALUES ("desk1", ?, "receptionist", "Front Desk")', 
                    (hash_password("desk123"),))
        
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Data already exists
    
    conn.close()
    
    print("Hotel Management System Backend Starting...")
    print("API Endpoints:")
    print("- GET /api/rooms - Get all rooms")
    print("- POST /api/rooms - Add new room")
    print("- POST /api/guests - Register guest")
    print("- POST /api/bookings - Create booking")
    print("- GET /api/bookings - Get all bookings")
    print("- POST /api/staff/login - Staff login")
    print("- GET /api/dashboard/stats - Dashboard statistics")
    
    app.run(debug=True, host='0.0.0.0', port=5000)