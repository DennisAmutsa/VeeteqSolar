from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import urllib.parse
import mysql.connector
from mysql.connector import Error
import os
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# WhatsApp Configuration
WHATSAPP_NUMBER = '254720426780'

@app.context_processor
def inject_settings():
    """Make settings available to all templates"""
    return {
        'company_name': get_setting('company_name', 'Veeteq Solar'),
        'default_currency': get_setting('default_currency', 'KSh')
    }


# Database configuration for XAMPP MySQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'veeteq_solar',
    'user': 'root',
    'password': ''  # Default XAMPP password is empty
}

def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_setting(key, default_value=None):
    """Get a setting value from the database"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT setting_value, setting_type FROM settings WHERE setting_key = %s", (key,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            value = result['setting_value']
            setting_type = result['setting_type']
            
            # Convert value based on type
            if setting_type == 'boolean':
                return value.lower() == 'true'
            elif setting_type == 'number':
                try:
                    return float(value) if '.' in value else int(value)
                except ValueError:
                    return default_value
            else:
                return value
        
        return default_value
    return default_value

def set_setting(key, value, setting_type='string', description=None):
    """Set a setting value in the database"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Convert value to string for storage
        if setting_type == 'boolean':
            value_str = 'true' if value else 'false'
        else:
            value_str = str(value)
        
        
        cursor.execute("""
            INSERT INTO settings (setting_key, setting_value, setting_type, description) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            setting_value = VALUES(setting_value),
            setting_type = VALUES(setting_type),
            description = VALUES(description),
            updated_at = CURRENT_TIMESTAMP
        """, (key, value_str, setting_type, description))
        
        cursor.close()
        connection.close()
        return True
    return False

def get_all_settings():
    """Get all settings as a dictionary"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT setting_key, setting_value, setting_type, description FROM settings")
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        
        settings = {}
        for result in results:
            key = result['setting_key']
            value = result['setting_value']
            setting_type = result['setting_type']
            
            # Convert value based on type
            if setting_type == 'boolean':
                settings[key] = value.lower() == 'true'
            elif setting_type == 'number':
                try:
                    settings[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    settings[key] = value
            else:
                settings[key] = value
        
        return settings
    return {}


def init_db():
    """Initialize database with required tables"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Create database if not exists
        cursor.execute("CREATE DATABASE IF NOT EXISTS veeteq_solar")
        cursor.execute("USE veeteq_solar")
        
        # Create tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                wattage INT,
                efficiency DECIMAL(5,2),
                warranty_years INT,
                manufacturer VARCHAR(100),
                image_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT,
                property_type VARCHAR(50),
                roof_size DECIMAL(8,2),
                energy_usage DECIMAL(8,2),
                system_size DECIMAL(8,2),
                estimated_cost DECIMAL(10,2),
                estimated_savings DECIMAL(10,2),
                status VARCHAR(20) DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS installations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT,
                quote_id INT,
                installation_date DATE,
                system_size DECIMAL(8,2),
                total_cost DECIMAL(10,2),
                status VARCHAR(50) DEFAULT 'scheduled',
                technician VARCHAR(100),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (quote_id) REFERENCES quotes(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                phone VARCHAR(20),
                address TEXT,
                city VARCHAR(50),
                state VARCHAR(50),
                zip_code VARCHAR(10),
                role VARCHAR(20) DEFAULT 'client',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                image_url VARCHAR(255) NOT NULL,
                category VARCHAR(50) DEFAULT 'installation',
                location VARCHAR(100),
                system_size DECIMAL(8,2),
                installation_date DATE,
                is_featured BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type VARCHAR(20) DEFAULT 'string',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        # Add manufacturer column to products table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE products ADD COLUMN manufacturer VARCHAR(100)")
            print("Added manufacturer column to products table")
        except Exception as e:
            # Column might already exist, ignore the error
            pass
        
        # Insert default admin user (username: admin, password: admin123)
        admin_hash = generate_password_hash('admin123')
        cursor.execute("""
            INSERT IGNORE INTO users (username, password_hash, email, first_name, last_name, role) 
            VALUES ('admin', %s, 'admin@veeteqsolar.com', 'Admin', 'User', 'admin')
        """, (admin_hash,))
        
        # Insert default settings
        default_settings = [
            ('dark_mode', 'false', 'boolean', 'Enable dark mode for the application'),
            ('email_notifications', 'true', 'boolean', 'Send email alerts for new quotes'),
            ('company_name', 'Veeteq Solar', 'string', 'Company name displayed on the website'),
            ('default_currency', 'KSh', 'string', 'Default currency for pricing'),
            ('session_timeout', '30', 'number', 'Session timeout in minutes'),
            ('max_login_attempts', '5', 'number', 'Maximum login attempts before lockout'),
            ('cost_per_watt_residential', '375', 'number', 'Cost per watt for residential installations (KSh)'),
            ('cost_per_watt_commercial', '325', 'number', 'Cost per watt for commercial installations (KSh)'),
            ('savings_per_kwh', '20', 'number', 'Savings per kWh generated (KSh)')
        ]
        
        for key, value, setting_type, description in default_settings:
            cursor.execute("""
                INSERT IGNORE INTO settings (setting_key, setting_value, setting_type, description) 
                VALUES (%s, %s, %s, %s)
            """, (key, value, setting_type, description))
        
        # Drop old tables if they exist (for migration from old system)
        try:
            cursor.execute("DROP TABLE IF EXISTS admin_users")
            cursor.execute("DROP TABLE IF EXISTS client_users")
            cursor.execute("DROP TABLE IF EXISTS customers")
            print("Old admin_users, client_users, and customers tables removed successfully!")
        except Exception as e:
            print(f"Note: Old tables may not exist yet: {e}")
        
        # Update foreign key constraints for quotes and installations
        try:
            # Remove old foreign key constraints
            cursor.execute("ALTER TABLE quotes DROP FOREIGN KEY IF EXISTS quotes_ibfk_1")
            cursor.execute("ALTER TABLE installations DROP FOREIGN KEY IF EXISTS installations_ibfk_1")
            print("Old foreign key constraints removed successfully!")
        except Exception as e:
            print(f"Note: Foreign key constraints may not exist yet: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        print("Database initialized successfully!")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/products')
def products():
    connection = get_db_connection()
    products = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY category, name")
        products = cursor.fetchall()
        cursor.close()
        connection.close()
    return render_template('products.html', products=products)

@app.route('/quote')
def quote():
    return render_template('quote.html')

@app.route('/calculate_quote', methods=['POST'])
def calculate_quote():
    try:
        data = request.json
        
        # Basic solar calculation logic
        monthly_usage = float(data.get('monthlyUsage', 0))
        roof_size = float(data.get('roofSize', 0))
        property_type = data.get('propertyType', 'residential')
        
        # Calculate system size (kW) based on monthly usage
        # Hybrid System Sizing: Factor 1.8x to cover Day Loads + Battery Charging
        # Assume 1 kW generates ~135 kWh per month on average (Improved efficiency/sun hours)
        required_kwh_monthly = monthly_usage * 1.8
        system_size_kw = required_kwh_monthly / 135
        
        # Limit by roof size (assume 1 kW needs ~100 sq ft)
        # If roof_size is the default 2000 sent by frontend, treat it as effectively unlimited
        if roof_size == 2000:
            roof_size = 5000000 # Boost to 5 million sq ft to allow industrial scale quotes
            
        max_system_by_roof = roof_size / 100
        system_size_kw = min(system_size_kw, max_system_by_roof)
        
        # Calculate panel count (assuming 550W panels)
        import math
        panel_count = max(6, math.ceil(system_size_kw / 0.55))
        
        # Recalculate exact system size based on panel count
        real_system_size_kw = panel_count * 0.55
        
        # Calculate costs (in Kenyan Shillings) - using dynamic settings
        if property_type == 'residential':
            cost_per_watt = get_setting('cost_per_watt_residential', 210)
        else:
            cost_per_watt = get_setting('cost_per_watt_commercial', 180)
        
        system_cost = real_system_size_kw * 1000 * cost_per_watt
        
        # Calculate savings using dynamic settings
        annual_generation = real_system_size_kw * 1200  # kWh per year
        savings_per_kwh = get_setting('savings_per_kwh', 20)
        annual_savings = annual_generation * savings_per_kwh
        
        # No tax credit in Kenya, but we can show the full system cost
        tax_credit = 0
        net_cost = system_cost
        
        result = {
            'systemSize': round(real_system_size_kw, 2),
            'panelCount': panel_count,
            'systemCost': round(system_cost, 2),
            'taxCredit': round(tax_credit, 2),
            'netCost': round(net_cost, 2),
            'annualSavings': round(annual_savings, 2),
            'paybackPeriod': round(net_cost / annual_savings, 1) if annual_savings > 0 else 0
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/submit_quote', methods=['POST'])
def submit_quote():
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zipCode', '')
        
        property_type = request.form.get('propertyType')
        roof_size = float(request.form.get('roofSize', 0))
        monthly_usage = float(request.form.get('monthlyUsage', 0))
        system_size = float(request.form.get('systemSize', 0))
        estimated_cost = float(request.form.get('estimatedCost', 0))
        estimated_savings = float(request.form.get('estimatedSavings', 0))
        panel_count = request.form.get('panelCount', '0')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                customer_id = existing_user[0]
                # Update user info if needed
                cursor.execute("""
                    UPDATE users SET phone = %s, address = %s, city = %s, state = %s, zip_code = %s
                    WHERE id = %s
                """, (phone, address, city, state, zip_code, customer_id))
            else:
                # Create new user with role 'client'
                cursor.execute("""
                    INSERT INTO users (username, email, phone, address, city, state, zip_code, role, first_name, last_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (name, email, phone, address, city, state, zip_code, 'client', name.split()[0] if name else '', name.split()[-1] if name and len(name.split()) > 1 else ''))
                customer_id = cursor.lastrowid
            
            # Insert quote
            cursor.execute("""
                INSERT INTO quotes (customer_id, property_type, roof_size, energy_usage, 
                                  system_size, estimated_cost, estimated_savings, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, property_type, roof_size, monthly_usage, 
                  system_size, estimated_cost, estimated_savings, 'pending'))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            # WhatsApp Integration
            try:
                # Format message for WhatsApp
                message = f"Hello Veeteq Solar, I would like to proceed with my quote request:\n\n"
                message += f"*Name:* {name}\n"
                message += f"*Location:* {address} ({city}, {state})\n"
                if phone:
                    message += f"*Phone:* {phone}\n"
                message += f"\n*System Details:*\n"
                message += f"- Property: {property_type.title()}\n"
                message += f"- Monthly Usage: {monthly_usage} KSh\n"
                if system_size:
                    message += f"- System Size: {panel_count} Panels ({system_size} kW)\n"
                if estimated_cost:
                    message += f"- Est. Cost: {estimated_cost:,.2f} KSh\n"
                
                encoded_message = urllib.parse.quote(message)
                whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_message}"
                
                flash('Quote submitted! Redirecting to WhatsApp...', 'success')
                return redirect(whatsapp_url)
                
            except Exception as e:
                print(f"WhatsApp redirect error: {str(e)}")
                flash('Quote request submitted successfully! We will contact you soon.', 'success')
                return redirect(url_for('quote'))
    
    except Exception as e:
        flash(f'Error submitting quote: {str(e)}', 'error')
        return redirect(url_for('quote'))

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/portfolio')
def portfolio():
    connection = get_db_connection()
    portfolio_items = []
    stats = {}
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get portfolio items
        cursor.execute("""
            SELECT * FROM portfolio 
            ORDER BY created_at DESC
        """)
        portfolio_items = cursor.fetchall()
        
        # Get portfolio stats
        cursor.execute("SELECT COUNT(*) as count FROM portfolio")
        portfolio_count = cursor.fetchone()['count']
        stats['total_projects'] = portfolio_count if portfolio_count > 0 else 0
        
        cursor.execute("SELECT SUM(system_size) as total_capacity FROM portfolio WHERE system_size IS NOT NULL")
        total_capacity = cursor.fetchone()['total_capacity']
        stats['total_capacity'] = float(total_capacity) if total_capacity else 0.0
        
        cursor.execute("SELECT COUNT(*) as count FROM installations WHERE status = 'completed'")
        completed_count = cursor.fetchone()['count']
        # Show realistic default values when database is empty
        stats['completed_installations'] = completed_count if completed_count > 0 else 1200
        
        cursor.execute("SELECT SUM(total_cost) as revenue FROM installations WHERE status = 'completed'")
        revenue = cursor.fetchone()['revenue']
        # Show realistic default revenue when database is empty
        stats['total_revenue'] = float(revenue) if revenue else 15000000  # 15M KSh default
        
        cursor.close()
        connection.close()
    
    return render_template('portfolio.html', portfolio_items=portfolio_items, stats=stats)

# Unified login routes
@app.route('/login')
def login():
    if 'user' in session:
        # Redirect based on user role
        if session['user']['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND is_active = TRUE", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'role': user['role']
            }
            
            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('client_dashboard'))
    
    flash('Invalid credentials', 'error')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    stats = {}
    recent_quotes = []
    customers = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'client'")
        stats['customers'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM quotes WHERE status = 'pending'")
        stats['quotes'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM installations")
        stats['installations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(estimated_cost) as total FROM quotes WHERE status = 'approved'")
        result = cursor.fetchone()
        stats['revenue'] = result['total'] if result['total'] else 0
        
        # Get all lists for the dashboard calculations
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email as customer_email
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE u.role = 'client'
            ORDER BY q.created_at DESC 
        """)
        quotes = cursor.fetchall()
        
        cursor.execute("SELECT * FROM users WHERE role = 'client' ORDER BY created_at DESC")
        clients = cursor.fetchall()
        
        cursor.execute("""
            SELECT i.*, u.first_name, u.last_name, q.property_type
            FROM installations i
            JOIN users u ON i.customer_id = u.id
            JOIN quotes q ON i.quote_id = q.id
            ORDER BY i.installation_date DESC
        """)
        installations = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin_dashboard.html', stats=stats, quotes=quotes, clients=clients, installations=installations)

@app.route('/admin/customers')
def admin_customers():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    customers = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE role = 'client' ORDER BY created_at DESC")
        customers = cursor.fetchall()
        cursor.close()
        connection.close()
    
    return render_template('admin_customers.html', customers=customers)

@app.route('/admin/customers/add', methods=['GET', 'POST'])
def admin_add_customer():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        
        # Check if username or email already exists
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash('Username or email already exists', 'error')
                cursor.close()
                connection.close()
                return redirect(url_for('admin_add_customer'))
            
            # Create new user with 'client' role
            password_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, first_name, last_name, phone, address, city, state, zip_code, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'client')
            """, (username, password_hash, email, first_name, last_name, phone, address, city, state, zip_code))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Client user added successfully!', 'success')
            return redirect(url_for('admin_customers'))
    
    return render_template('admin_add_customer.html')

@app.route('/admin/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def admin_edit_customer(customer_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    customer = None
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'client'", (customer_id,))
        customer = cursor.fetchone()
        
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            address = request.form.get('address')
            city = request.form.get('city')
            state = request.form.get('state')
            zip_code = request.form.get('zip_code')
            
            cursor.execute("""
                UPDATE users 
                SET username = %s, email = %s, first_name = %s, last_name = %s, phone = %s, address = %s, city = %s, state = %s, zip_code = %s
                WHERE id = %s
            """, (username, email, first_name, last_name, phone, address, city, state, zip_code, customer_id))
            connection.commit()
            flash('Client user updated successfully!', 'success')
            return redirect(url_for('admin_customers'))
        
        cursor.close()
        connection.close()
    
    if not customer:
        flash('Client user not found!', 'error')
        return redirect(url_for('admin_customers'))
    
    return render_template('admin_edit_customer.html', customer=customer)

@app.route('/admin/customers/delete/<int:customer_id>', methods=['POST'])
def admin_delete_customer(customer_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s AND role = 'client'", (customer_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Client user deleted successfully!', 'success')
    
    return redirect(url_for('admin_customers'))

@app.route('/admin/quotes')
def admin_quotes():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    quotes = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email, u.phone 
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE u.role = 'client'
            ORDER BY q.created_at DESC
        """)
        quotes = cursor.fetchall()
        cursor.close()
        connection.close()
    
    return render_template('admin_quotes.html', quotes=quotes)

@app.route('/admin/quotes/approve/<int:quote_id>', methods=['POST'])
def admin_approve_quote(quote_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE quotes SET status = 'approved' WHERE id = %s", (quote_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Quote approved successfully!', 'success')
    
    return redirect(url_for('admin_quotes'))

@app.route('/admin/quotes/reject/<int:quote_id>', methods=['POST'])
def admin_reject_quote(quote_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("UPDATE quotes SET status = 'rejected' WHERE id = %s", (quote_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Quote rejected successfully!', 'success')
    
    return redirect(url_for('admin_quotes'))

@app.route('/admin/quotes/view/<int:quote_id>')
def admin_view_quote(quote_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    quote = None
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email, u.phone, u.address, u.city, u.state, u.zip_code
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE q.id = %s
        """, (quote_id,))
        quote = cursor.fetchone()
        cursor.close()
        connection.close()
    
    if not quote:
        flash('Quote not found!', 'error')
        return redirect(url_for('admin_quotes'))
    
    return render_template('admin_view_quote.html', quote=quote)

@app.route('/admin/quotes/edit/<int:quote_id>', methods=['GET', 'POST'])
def admin_edit_quote(quote_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    quote = None
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email, u.phone, u.address, u.city, u.state, u.zip_code
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE q.id = %s
        """, (quote_id,))
        quote = cursor.fetchone()
        
        if request.method == 'POST':
            property_type = request.form.get('property_type')
            roof_size = float(request.form.get('roof_size', 0))
            energy_usage = float(request.form.get('energy_usage', 0))
            system_size = float(request.form.get('system_size', 0))
            estimated_cost = float(request.form.get('estimated_cost', 0))
            estimated_savings = float(request.form.get('estimated_savings', 0))
            status = request.form.get('status')
            notes = request.form.get('notes')
            
            cursor.execute("""
                UPDATE quotes 
                SET property_type = %s, roof_size = %s, energy_usage = %s, system_size = %s, 
                    estimated_cost = %s, estimated_savings = %s, status = %s, notes = %s
                WHERE id = %s
            """, (property_type, roof_size, energy_usage, system_size, estimated_cost, estimated_savings, status, notes, quote_id))
            connection.commit()
            flash('Quote updated successfully!', 'success')
            return redirect(url_for('admin_quotes'))
        
        cursor.close()
        connection.close()
    
    if not quote:
        flash('Quote not found!', 'error')
        return redirect(url_for('admin_quotes'))
    
    return render_template('admin_edit_quote.html', quote=quote)


# Registration route
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    phone = request.form.get('phone')
    
    # Validation
    if password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('register'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('register'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Check if username or email already exists
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Username or email already exists', 'error')
            cursor.close()
            connection.close()
            return redirect(url_for('register'))
        
        # Create new user with 'client' role by default
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, first_name, last_name, phone, role)
            VALUES (%s, %s, %s, %s, %s, %s, 'client')
        """, (username, password_hash, email, first_name, last_name, phone))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))
    
    flash('Registration failed. Please try again.', 'error')
    return redirect(url_for('register'))

@app.route('/client/dashboard')
def client_dashboard():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))
    
    user_id = session['user']['id']
    user_email = session['user']['email']
    
    connection = get_db_connection()
    quotes = []
    installations = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get user's quotes
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email 
            FROM quotes q 
            JOIN users u ON q.customer_id = u.id 
            WHERE u.email = %s 
            ORDER BY q.created_at DESC
        """, (user_email,))
        quotes = cursor.fetchall()
        
        # Get user's installations
        cursor.execute("""
            SELECT i.*, u.first_name, u.last_name, u.email 
            FROM installations i 
            JOIN users u ON i.customer_id = u.id 
            WHERE u.email = %s 
            ORDER BY i.created_at DESC
        """, (user_email,))
        installations = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('client_dashboard.html', quotes=quotes, installations=installations)

@app.route('/client/quotes')
def client_quotes():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))
    
    user_email = session['user']['email']
    connection = get_db_connection()
    quotes = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get user's quotes
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email 
            FROM quotes q 
            JOIN users u ON q.customer_id = u.id 
            WHERE u.email = %s 
            ORDER BY q.created_at DESC
        """, (user_email,))
        quotes = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('client_quotes.html', quotes=quotes)

@app.route('/client/installations')
def client_installations():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))
    
    user_email = session['user']['email']
    connection = get_db_connection()
    installations = []
    
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get user's installations
        cursor.execute("""
            SELECT i.*, u.first_name, u.last_name, u.email 
            FROM installations i 
            JOIN users u ON i.customer_id = u.id 
            WHERE u.email = %s 
            ORDER BY i.created_at DESC
        """, (user_email,))
        installations = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('client_installations.html', installations=installations)

@app.route('/client/profile')
def client_profile():
    user_id = session['user']['id']
    user = None
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
    
    return render_template('client_profile.html', user=user)

@app.route('/client/profile/update', methods=['POST'])
def client_profile_update():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))
    
    user_id = session['user']['id']
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    city = request.form.get('city')
    state = request.form.get('state')
    zip_code = request.form.get('zip_code')
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s, email = %s, phone = %s, 
                address = %s, city = %s, state = %s, zip_code = %s
            WHERE id = %s
        """, (first_name, last_name, email, phone, address, city, state, zip_code, user_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        # Update session data
        session['user']['email'] = email
        session['user']['first_name'] = first_name
        session['user']['last_name'] = last_name
        
        flash('Profile updated successfully!', 'success')
    else:
        flash('Failed to update profile', 'error')
    
    return redirect(url_for('client_profile'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# Portfolio Management Routes
@app.route('/admin/portfolio')
def admin_portfolio():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    portfolio_items = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM portfolio ORDER BY created_at DESC")
        portfolio_items = cursor.fetchall()
        cursor.close()
        connection.close()
    
    return render_template('admin_portfolio.html', portfolio_items=portfolio_items)

@app.route('/admin/portfolio/add', methods=['GET', 'POST'])
def admin_add_portfolio():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        system_size = request.form.get('system_size')
        installation_date = request.form.get('installation_date')
        is_featured = request.form.get('is_featured') == 'on'
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = f"portfolio_{int(time.time())}_{file.filename}"
                file.save(os.path.join('static/uploads', filename))
                image_url = f"/static/uploads/{filename}"
            else:
                image_url = "/static/uploads/placeholder.jpg"
        else:
            image_url = "/static/uploads/placeholder.jpg"
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO portfolio (title, description, image_url, category, location, system_size, installation_date, is_featured)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (title, description, image_url, category, location, system_size, installation_date, is_featured))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Portfolio item added successfully!', 'success')
            return redirect(url_for('admin_portfolio'))
    
    return render_template('admin_add_portfolio.html')

@app.route('/admin/portfolio/edit/<int:item_id>', methods=['GET', 'POST'])
def admin_edit_portfolio(item_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    item = None
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM portfolio WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            location = request.form.get('location')
            system_size = request.form.get('system_size')
            installation_date = request.form.get('installation_date')
            is_featured = request.form.get('is_featured') == 'on'
            
            # Handle file upload
            image_url = item['image_url']  # Keep existing image by default
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    filename = f"portfolio_{int(time.time())}_{file.filename}"
                    file.save(os.path.join('static/uploads', filename))
                    image_url = f"/static/uploads/{filename}"
            
            cursor.execute("""
                UPDATE portfolio 
                SET title = %s, description = %s, image_url = %s, category = %s, location = %s, system_size = %s, installation_date = %s, is_featured = %s
                WHERE id = %s
            """, (title, description, image_url, category, location, system_size, installation_date, is_featured, item_id))
            connection.commit()
            flash('Portfolio item updated successfully!', 'success')
            return redirect(url_for('admin_portfolio'))
        
        cursor.close()
        connection.close()
    
    if not item:
        flash('Portfolio item not found!', 'error')
        return redirect(url_for('admin_portfolio'))
    
    return render_template('admin_edit_portfolio.html', item=item)

@app.route('/admin/portfolio/delete/<int:item_id>', methods=['POST'])
def admin_delete_portfolio(item_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM portfolio WHERE id = %s", (item_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Portfolio item deleted successfully!', 'success')
    
    return redirect(url_for('admin_portfolio'))

@app.route('/admin/promote_cedric')
def promote_cedric_to_admin():
    """Promote Cedric Sumba to admin using his existing account details"""
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        
        # Update Cedric's role to admin
        cursor.execute("UPDATE users SET role = 'admin' WHERE email = 'sumbacedric@gmail.com'")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Cedric Sumba has been promoted to admin successfully!")
        return "Cedric Sumba is now an admin! He can login at /login and will be redirected to admin dashboard."
    
    return "Database connection failed."

# Product Management Routes
@app.route('/admin/products')
def admin_products():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    products = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY category, name")
        products = cursor.fetchall()
        cursor.close()
        connection.close()
    
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        price = float(request.form.get('price', 0))
        wattage = int(request.form.get('wattage', 0)) if request.form.get('wattage') else 0
        efficiency = float(request.form.get('efficiency', 0)) if request.form.get('efficiency') else 0
        warranty_years = int(request.form.get('warranty_years', 0)) if request.form.get('warranty_years') else 0
        manufacturer = request.form.get('manufacturer', '')
        
        # Handle file upload
        image_url = "/static/uploads/placeholder.jpg"  # Default image
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = f"product_{int(time.time())}_{file.filename}"
                file.save(os.path.join('static/uploads', filename))
                image_url = f"/static/uploads/{filename}"
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO products (name, description, category, price, wattage, efficiency, warranty_years, manufacturer, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, description, category, price, wattage, efficiency, warranty_years, manufacturer, image_url))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
    
    return render_template('admin_add_product.html')

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Product deleted successfully!', 'success')
    
    return redirect(url_for('admin_products'))

# Installation Management Routes
@app.route('/admin/installations')
def admin_installations():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    installations = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.*, u.first_name, u.last_name, u.email, u.phone, q.system_size as quote_system_size
            FROM installations i 
            LEFT JOIN users u ON i.customer_id = u.id 
            LEFT JOIN quotes q ON i.quote_id = q.id
            WHERE u.role = 'client'
            ORDER BY i.created_at DESC
        """)
        installations = cursor.fetchall()
        cursor.close()
        connection.close()
    
    return render_template('admin_installations.html', installations=installations)

@app.route('/admin/installations/add', methods=['GET', 'POST'])
def admin_add_installation():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    quotes = []
    users = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get pending quotes for selection
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE q.status = 'approved' AND u.role = 'client'
            ORDER BY q.created_at DESC
        """)
        quotes = cursor.fetchall()
        
        # Get client users
        cursor.execute("SELECT * FROM users WHERE role = 'client' ORDER BY first_name, last_name")
        users = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        quote_id = request.form.get('quote_id')
        installation_date = request.form.get('installation_date')
        system_size = request.form.get('system_size')
        total_cost = request.form.get('total_cost')
        status = request.form.get('status')
        technician = request.form.get('technician')
        notes = request.form.get('notes')
        
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO installations (customer_id, quote_id, installation_date, system_size, total_cost, status, technician, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, quote_id, installation_date, system_size, total_cost, status, technician, notes))
            connection.commit()
            cursor.close()
            connection.close()
            flash('Installation scheduled successfully!', 'success')
            return redirect(url_for('admin_installations'))
    
    return render_template('admin_add_installation.html', quotes=quotes, users=users)

@app.route('/admin/installations/edit/<int:installation_id>', methods=['GET', 'POST'])
def admin_edit_installation(installation_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    installation = None
    quotes = []
    users = []
    if connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM installations WHERE id = %s", (installation_id,))
        installation = cursor.fetchone()
        
        # Get quotes and users for dropdowns
        cursor.execute("""
            SELECT q.*, u.first_name, u.last_name, u.email
            FROM quotes q 
            LEFT JOIN users u ON q.customer_id = u.id 
            WHERE q.status = 'approved' AND u.role = 'client'
            ORDER BY q.created_at DESC
        """)
        quotes = cursor.fetchall()
        
        cursor.execute("SELECT * FROM users WHERE role = 'client' ORDER BY first_name, last_name")
        users = cursor.fetchall()
        
        if request.method == 'POST':
            customer_id = request.form.get('customer_id')
            quote_id = request.form.get('quote_id')
            installation_date = request.form.get('installation_date')
            system_size = request.form.get('system_size')
            total_cost = request.form.get('total_cost')
            status = request.form.get('status')
            technician = request.form.get('technician')
            notes = request.form.get('notes')
            
            cursor.execute("""
                UPDATE installations 
                SET customer_id = %s, quote_id = %s, installation_date = %s, system_size = %s, total_cost = %s, status = %s, technician = %s, notes = %s
                WHERE id = %s
            """, (customer_id, quote_id, installation_date, system_size, total_cost, status, technician, notes, installation_id))
            connection.commit()
            flash('Installation updated successfully!', 'success')
            return redirect(url_for('admin_installations'))
        
        cursor.close()
        connection.close()
    
    if not installation:
        flash('Installation not found!', 'error')
        return redirect(url_for('admin_installations'))
    
    return render_template('admin_edit_installation.html', installation=installation, quotes=quotes, users=users)

@app.route('/admin/installations/delete/<int:installation_id>', methods=['POST'])
def admin_delete_installation(installation_id):
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM installations WHERE id = %s", (installation_id,))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Installation deleted successfully!', 'success')
    
    return redirect(url_for('admin_installations'))

# Analytics Route
@app.route('/admin/analytics')
def admin_analytics():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    analytics = {}
    if connection:
        cursor = connection.cursor(dictionary=True)
        
        # Get various analytics data
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'client'")
        analytics['total_clients'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM quotes")
        analytics['total_quotes'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM quotes WHERE status = 'pending'")
        analytics['pending_quotes'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM quotes WHERE status = 'approved'")
        analytics['approved_quotes'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM installations")
        analytics['total_installations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM installations WHERE status = 'completed'")
        analytics['completed_installations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM installations WHERE status = 'scheduled'")
        analytics['scheduled_installations'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM portfolio")
        analytics['portfolio_items'] = cursor.fetchone()['count']
        
        # Revenue analytics
        cursor.execute("SELECT SUM(total_cost) as revenue FROM installations WHERE status = 'completed'")
        revenue = cursor.fetchone()['revenue']
        analytics['total_revenue'] = revenue if revenue else 0
        
        cursor.execute("SELECT SUM(estimated_cost) as potential FROM quotes WHERE status = 'approved'")
        potential = cursor.fetchone()['potential']
        analytics['potential_revenue'] = potential if potential else 0
        
        # Monthly stats
        cursor.execute("""
            SELECT DATE_FORMAT(created_at, '%Y-%m') as month, COUNT(*) as count 
            FROM quotes 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month DESC
        """)
        analytics['monthly_quotes'] = cursor.fetchall()
        
        cursor.execute("""
            SELECT DATE_FORMAT(installation_date, '%Y-%m') as month, COUNT(*) as count 
            FROM installations 
            WHERE installation_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(installation_date, '%Y-%m')
            ORDER BY month DESC
        """)
        analytics['monthly_installations'] = cursor.fetchall()
        
        cursor.close()
        connection.close()
    
    return render_template('admin_analytics.html', analytics=analytics)


@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Get form data
            email_notifications = request.form.get('email_notifications') == 'on'
            company_name = request.form.get('company_name', '').strip()
            default_currency = request.form.get('default_currency', 'KSh')
            session_timeout = int(request.form.get('session_timeout', 30))
            max_login_attempts = int(request.form.get('max_login_attempts', 5))
            cost_per_watt_residential = float(request.form.get('cost_per_watt_residential', 375))
            cost_per_watt_commercial = float(request.form.get('cost_per_watt_commercial', 325))
            savings_per_kwh = float(request.form.get('savings_per_kwh', 20))
            
            # Validate inputs
            if session_timeout < 5 or session_timeout > 480:
                flash('Session timeout must be between 5 and 480 minutes', 'error')
                return redirect(url_for('admin_settings'))
            
            if max_login_attempts < 3 or max_login_attempts > 10:
                flash('Max login attempts must be between 3 and 10', 'error')
                return redirect(url_for('admin_settings'))
            
            if cost_per_watt_residential < 100 or cost_per_watt_residential > 1000:
                flash('Residential cost per watt must be between 100 and 1000 KSh', 'error')
                return redirect(url_for('admin_settings'))
            
            if cost_per_watt_commercial < 100 or cost_per_watt_commercial > 1000:
                flash('Commercial cost per watt must be between 100 and 1000 KSh', 'error')
                return redirect(url_for('admin_settings'))
            
            if savings_per_kwh < 5 or savings_per_kwh > 100:
                flash('Savings per kWh must be between 5 and 100 KSh', 'error')
                return redirect(url_for('admin_settings'))
            
            # Save settings
            set_setting('email_notifications', email_notifications, 'boolean', 'Send email alerts for new quotes')
            set_setting('company_name', company_name, 'string', 'Company name displayed on the website')
            set_setting('default_currency', default_currency, 'string', 'Default currency for pricing')
            set_setting('session_timeout', session_timeout, 'number', 'Session timeout in minutes')
            set_setting('max_login_attempts', max_login_attempts, 'number', 'Maximum login attempts before lockout')
            set_setting('cost_per_watt_residential', cost_per_watt_residential, 'number', 'Cost per watt for residential installations (KSh)')
            set_setting('cost_per_watt_commercial', cost_per_watt_commercial, 'number', 'Cost per watt for commercial installations (KSh)')
            set_setting('savings_per_kwh', savings_per_kwh, 'number', 'Savings per kWh generated (KSh)')
            
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('admin_settings'))
            
        except ValueError as e:
            flash('Invalid input values. Please check your entries.', 'error')
            return redirect(url_for('admin_settings'))
        except Exception as e:
            flash('An error occurred while saving settings.', 'error')
            return redirect(url_for('admin_settings'))
    
    # Load current settings for GET request
    settings = get_all_settings()
    return render_template('admin_settings.html', settings=settings)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    from flask import send_from_directory
    import os
    static_folder = os.path.join(app.root_path, 'static', 'uploads')
    return send_from_directory(static_folder, 'Veeteq Solar.jpg', mimetype='image/jpeg')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
