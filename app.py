#!/usr/bin/env python3
"""
Simple WhatsApp CRM Web App
- Add/List Customers
- View Informed List (Sent Logs)
- Import Customers from Excel
- Uses SQLite3 database
"""

import os
import sqlite3
import threading
import requests
import random
import time
import pytz
import logging
import json
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from werkzeug.utils import secure_filename
import io

# --- Main Application Setup ---
app = Flask(__name__)

# --- Configuration ---
# Database file path - stored in the same directory as the app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'crm.db'))

WAHA_URL = os.getenv('WAHA_URL', 'http://localhost:3000')
WAHA_API_KEY = os.getenv('WAHA_API_KEY', 'YOUR_WAHA_API_KEY')
SESSION = os.getenv('WAHA_SESSION', 'default')

UPLOAD_FOLDER = '/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Timezone
UAE_TZ = pytz.timezone('Asia/Dubai')

# Fixed Template for Automated Sending Logic
FIXED_TEMPLATE = "Dear {customer_name}, your {visa_type} visa would be expired on {visa_expiry_date}, kindly renew it. Today's date: {today_date}"

# --- Helper Functions ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    except Exception as e:
        app.logger.error(f"DATABASE CONNECTION FAILED: {e}")
        return None

def get_waha_headers():
    """Returns headers required for WAHA API requests if API key is set."""
    if WAHA_API_KEY and WAHA_API_KEY != "YOUR_WAHA_API_KEY": # Avoid sending if not set
        return {"Authorization": f"Bearer {WAHA_API_KEY}"}
    return {} # Return empty dict if no key

# ===================================================================
# Main Page: Customer Input, List, Informed List
# ===================================================================

@app.route('/')
def index():
    """Serves the main page."""
    return render_template('index.html')

# ===================================================================
# API Routes
# ===================================================================

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """API: Get all customers."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, customer_name, visa_type, date(visa_expiry_date) as visa_expiry_date, country_code, phone_number FROM customers ORDER BY id DESC')
        customers = []
        for row in cur.fetchall():
            customer_dict = dict(row)
            # Ensure visa_expiry_date is a string
            if customer_dict.get('visa_expiry_date'):
                customer_dict['visa_expiry_date'] = str(customer_dict['visa_expiry_date'])
            customers.append(customer_dict)
        cur.close()
        return jsonify(customers)
    except Exception as e:
        app.logger.error(f"Failed getting customers: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/customers', methods=['POST'])
def add_customer():
    """API: Add a new customer."""
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        # Basic validation
        if not data.get('name') or not data.get('visa_type') or not data.get('expiry_date'):
            return jsonify({'success': False, 'error': 'Missing required fields (Name, Visa Type, Expiry Date)'}), 400
        try:
            expiry_d = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            if expiry_d <= date.today():
                 return jsonify({'success': False, 'error': 'Expiry date must be in the future.'}), 400
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

        cur = conn.cursor()
        cur.execute(
            """INSERT INTO customers (customer_name, visa_type, visa_expiry_date, country_code, phone_number) VALUES (?, ?, ?, ?, ?)""",
            (data['name'], data['visa_type'], data['expiry_date'], data.get('country_code') or None, data.get('phone') or None)
        )
        conn.commit()
        cur.close()
        return jsonify({'success': True}), 201
    except sqlite3.IntegrityError as e:
        app.logger.warning(f"Add customer conflict: {e}")
        if "UNIQUE constraint" in str(e) or "unique constraint" in str(e).lower():
             return jsonify({'success': False, 'error': 'Customer with this name and expiry date already exists.'}), 409
        else: return jsonify({'success': False, 'error': f'Database integrity error: {e}'}), 400
    except Exception as e:
        app.logger.error(f"Failed to add customer: {e}")
        return jsonify({'success': False, 'error': f'An unexpected error occurred: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """API: Delete a customer."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        if cur.rowcount == 0: 
            cur.close()
            return jsonify({'success': False, 'error': 'Customer not found'}), 404
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        app.logger.error(f"Failed to delete customer {customer_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/informed-customers', methods=['GET'])
def get_informed_customers():
    """API: Get customers from send_logs."""
    filter_by = request.args.get('filter', 'all')
    query = "SELECT id, customer_name, phone, message, status, sent_at FROM send_logs"
    params = []
    if filter_by == 'today':
        today_date_uae = datetime.now(UAE_TZ).date()
        query += " WHERE DATE(sent_at) = ?"
        params.append(str(today_date_uae))
    query += " ORDER BY sent_at DESC LIMIT 500" # Limit results for performance
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        logs = []
        for row in cur.fetchall():
            log_dict = dict(row)
            # Handle sent_at datetime formatting
            if log_dict.get('sent_at'):
                try:
                    # Parse datetime string if it exists
                    dt = datetime.fromisoformat(log_dict['sent_at'].replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = UAE_TZ.localize(dt)
                    log_dict['sent_at'] = dt.astimezone(UAE_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
                except:
                    # If parsing fails, use as-is
                    log_dict['sent_at'] = str(log_dict['sent_at'])
            logs.append(log_dict)
        cur.close()
        return jsonify(logs)
    except Exception as e:
        app.logger.error(f"Failed to fetch send_logs: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# --- Excel Import Logic ---
def parse_date_flexible(date_value, row_num, errors):
    # Simplified parsing logic
    if pd.isna(date_value): return None
    if isinstance(date_value, datetime): return date_value.date()
    if hasattr(date_value, 'date') and callable(date_value.date): return date_value.date() # Pandas Timestamp
    if isinstance(date_value, str):
        date_str = str(date_value).strip().split(' ')[0]
        fmts = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%m-%d-%Y']
        for fmt in fmts:
            try: return datetime.strptime(date_str, fmt).date()
            except ValueError: continue
    try: # Excel numbers
        if isinstance(date_value, (int, float)):
             if date_value < 1: raise ValueError("Bad date number")
             origin = '1899-12-30'
             dt = pd.to_datetime(date_value, origin=origin, unit='D')
             if dt.year < 1950 or dt.year > 2100: raise ValueError("Year out of range")
             return dt.date()
    except Exception as e: app.logger.debug(f"Row {row_num} num date parse error: {e}")
    errors.append(f"Row {row_num}: Bad date format '{date_value}'")
    return None

@app.route('/api/import-excel', methods=['POST'])
def import_excel_preview():
    # ... (Excel preview logic - same as before)
    if 'excel-file' not in request.files: return jsonify({"errors": ["No file part"]}), 400
    file = request.files['excel-file']
    if not file or file.filename == '': return jsonify({"errors": ["No selected file"]}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        file.save(filepath)
        df = pd.read_excel(filepath)
        expected = ['Customer Name', 'Visa Type', 'Visa expiry date', 'CC', 'phone']
        df.columns = [str(col).strip() for col in df.columns]
        rename_map = {actual: exp for exp in expected for actual in df.columns if actual.lower() == exp.lower()}
        df.rename(columns=rename_map, inplace=True)
        missing = [col for col in expected if col not in df.columns]
        if missing: return jsonify({"errors": [f"Missing columns: {', '.join(missing)}"]}), 400

        data, errors = [], []
        app.logger.info(f"Processing {len(df)} rows from Excel...")
        for i, row in df.iterrows():
            row_num = i + 2
            try:
                if row.isnull().all(): continue
                name = str(row.get('Customer Name', '')).strip()
                if not name or pd.isna(row.get('Customer Name')): continue
                vtype = str(row.get('Visa Type', '')).strip()
                exp_raw = row.get('Visa expiry date')
                cc_raw = row.get('CC', '')
                ph_raw = row.get('phone', '')
                cc = str(int(cc_raw)).strip() if isinstance(cc_raw, (int, float)) and not pd.isna(cc_raw) else str(cc_raw).strip()
                cc = cc or None
                ph = str(int(ph_raw)).strip() if isinstance(ph_raw, (int, float)) and not pd.isna(ph_raw) else str(ph_raw).strip()
                if ph: ph = ''.join(filter(str.isdigit, ph))
                ph = ph or None
                if not vtype: errors.append(f"Row {row_num} ('{name}'): Missing Visa Type"); continue
                if pd.isna(exp_raw): errors.append(f"Row {row_num} ('{name}'): Missing Visa expiry date"); continue
                pdate = parse_date_flexible(exp_raw, row_num, errors)
                if pdate is None: continue
                if pdate <= date.today(): errors.append(f"Row {row_num} ('{name}'): Expiry date '{pdate}' is not in the future"); continue
                data.append({'customer_name': name, 'visa_type': vtype, 'expiry_date': pdate.strftime('%Y-%m-%d'), 'country_code': cc, 'phone_number': ph})
            except Exception as row_err:
                 app.logger.error(f"Error processing Excel row {row_num}: {row_err}", exc_info=True)
                 errors.append(f"Row {row_num}: Unexpected error processing row - {row_err}")
        app.logger.info(f"Excel preview generated. Valid records: {len(data)}, Errors: {len(errors)}")
        return jsonify({"data_to_preview": data, "errors": errors})
    except Exception as e: app.logger.error(f"Excel file processing error: {e}", exc_info=True); return jsonify({"errors": [f"Error processing Excel file: {e}"]}), 500
    finally:
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except Exception as rm_err: app.logger.warning(f"Could not remove temp file {filepath}: {rm_err}")

@app.route('/api/commit-import', methods=['POST'])
def commit_excel_import():
    # ... (Commit import logic - same as before)
    data = request.json.get('data')
    if not data: return jsonify({"error": "No data to import"}), 400
    conn, imported, skipped = get_db_connection(), 0, 0
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    app.logger.info(f"Attempting to commit {len(data)} records from Excel import...")
    try:
        cur = conn.cursor()
        for rec_idx, rec in enumerate(data):
            try:
                expiry_date = datetime.strptime(rec['expiry_date'], '%Y-%m-%d').date()
                cur.execute(
                    """INSERT INTO customers (customer_name, visa_type, visa_expiry_date, country_code, phone_number) VALUES (?, ?, ?, ?, ?) ON CONFLICT (customer_name, visa_expiry_date) DO NOTHING""",
                    (rec['customer_name'], rec['visa_type'], expiry_date, rec.get('country_code'), rec.get('phone_number'))
                )
                if cur.rowcount > 0: imported += 1
                else: skipped += 1; app.logger.debug(f"Skipped (duplicate): {rec['customer_name']} - {rec['expiry_date']}")
            except Exception as insert_err:
                app.logger.error(f"Import Insert Error record #{rec_idx} ({rec.get('customer_name')}): {insert_err}")
                skipped += 1
        conn.commit() # Commit all successful inserts
        cur.close()
        app.logger.info(f"Commit Import successful. Imported: {imported}, Skipped: {skipped}")
        return jsonify({"success": True, "imported": imported, "skipped": skipped})
    except Exception as e: app.logger.error(f"Commit Import Transaction Error: {e}", exc_info=True); return jsonify({"success": False, "error": f"DB transaction error: {e}"}), 500
    finally:
        if conn: conn.close()

# ===================================================================
# Automated Notification Logic (Explanation - Run Separately via Cron)
# ===================================================================

# NOTE: The actual sending should be done by a separate script scheduled with cron,
#       similar to your original `production_send_bulk.py`.
#       This avoids blocking the web server and handles scheduling reliably.

# Example logic for the separate cron script:
# 1. Connect to the database (using DB_HOST, DB_NAME, DB_USER, DB_PASS).
# 2. Get today's date in UAE timezone: today_uae = datetime.now(UAE_TZ).date()
# 3. Query customers expiring today:
#    SELECT id, customer_name, visa_type, visa_expiry_date, country_code, phone_number
#    FROM customers
#    WHERE visa_expiry_date = today_uae
# 4. For each customer found:
#    a. Construct the full phone number.
#    b. Format the FIXED_TEMPLATE message with customer details.
#    c. Prepare the WAHA API payload: {"chatId": "FULL_PHONE@c.us", "text": formatted_message, "session": SESSION}
#    d. Send the message using requests.post(f"{WAHA_URL}/api/sendText", json=payload, headers=get_waha_headers()).
#    e. Log the attempt (success/failure) to the `send_logs` table.
#    f. Add a random delay (e.g., 6-8 seconds) between messages.
# 5. Close the database connection.
# 6. Schedule this script using `crontab -e` to run at 3:00 UTC (7 AM UAE).

# ===================================================================
# Run Development Server
# ===================================================================
if __name__ == '__main__':
    # Development mode: use Flask's built-in server
    # Production: Use gunicorn (see systemd service file)
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 8080))
    logging.basicConfig(level=logging.DEBUG if debug_mode else logging.INFO, 
                       format='%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s')
    app.run(debug=debug_mode, host='0.0.0.0', port=port)