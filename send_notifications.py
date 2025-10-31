#!/usr/bin/env python3
"""
Automated Notification Script
Run this script via cron to send WhatsApp notifications to customers
whose visas expire today (UAE timezone).
"""

import os
import sys
import sqlite3
import requests
import random
import time
import pytz
import logging
from datetime import datetime, date

# --- Configuration from Environment Variables ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'crm.db'))

WAHA_URL = os.getenv('WAHA_URL', 'http://localhost:3000')
WAHA_API_KEY = os.getenv('WAHA_API_KEY', '')
SESSION = os.getenv('WAHA_SESSION', 'default')

# Timezone
UAE_TZ = pytz.timezone('Asia/Dubai')

# Fixed Template for Automated Sending Logic
FIXED_TEMPLATE = "Dear {customer_name}, your {visa_type} visa would be expired on {visa_expiry_date}, kindly renew it. Today's date: {today_date}"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    except Exception as e:
        logger.error(f"DATABASE CONNECTION FAILED: {e}")
        return None

def get_waha_headers():
    """Returns headers required for WAHA API requests."""
    if WAHA_API_KEY:
        return {"Authorization": f"Bearer {WAHA_API_KEY}"}
    return {}

def send_whatsapp_message(phone_number, message):
    """Sends a WhatsApp message via WAHA API."""
    try:
        # Format phone number for WhatsApp (remove + if present, add @c.us)
        phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        chat_id = f"{phone}@c.us"
        
        payload = {
            "chatId": chat_id,
            "text": message,
            "session": SESSION
        }
        
        headers = get_waha_headers()
        headers['Content-Type'] = 'application/json'
        
        response = requests.post(
            f"{WAHA_URL}/api/sendText",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Message sent successfully to {phone_number}")
            return True, "sent"
        else:
            error_msg = f"WAHA API error: {response.status_code} - {response.text}"
            logger.error(f"Failed to send to {phone_number}: {error_msg}")
            return False, f"failed: {error_msg}"
            
    except Exception as e:
        error_msg = f"Exception sending message: {str(e)}"
        logger.error(f"Failed to send to {phone_number}: {error_msg}")
        return False, f"error: {error_msg}"

def log_send_attempt(conn, customer_name, phone, message, status):
    """Logs the send attempt to the send_logs table."""
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO send_logs (customer_name, phone, message, status, sent_at) 
               VALUES (?, ?, ?, ?, datetime('now'))""",
            (customer_name, phone, message, status)
        )
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Failed to log send attempt: {e}")

def main():
    """Main function to process expiring visas and send notifications."""
    logger.info("=" * 60)
    logger.info("Starting automated notification process")
    logger.info("=" * 60)
    
    # Get today's date in UAE timezone
    today_uae = datetime.now(UAE_TZ).date()
    logger.info(f"Today's date (UAE): {today_uae}")
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        logger.error("Failed to connect to database. Exiting.")
        sys.exit(1)
    
    try:
        # Query customers expiring today
        cur = conn.cursor()
        cur.execute(
            """SELECT id, customer_name, visa_type, visa_expiry_date, country_code, phone_number 
               FROM customers 
               WHERE date(visa_expiry_date) = ?""",
            (str(today_uae),)
        )
        customers = cur.fetchall()
        cur.close()
        
        logger.info(f"Found {len(customers)} customers with visas expiring today")
        
        if len(customers) == 0:
            logger.info("No customers to notify. Exiting.")
            return
        
        # Process each customer
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        
        for customer in customers:
            customer_dict = dict(customer)
            customer_name = customer_dict['customer_name']
            visa_type = customer_dict['visa_type']
            visa_expiry_date = customer_dict['visa_expiry_date']
            country_code = customer_dict.get('country_code') or ''
            phone_number = customer_dict.get('phone_number') or ''
            
            # Construct full phone number
            full_phone = ''
            if country_code:
                full_phone += str(country_code).strip()
            if phone_number:
                full_phone += str(phone_number).strip()
            
            # Check if phone number is available
            if not full_phone:
                logger.warning(f"Skipping {customer_name}: No phone number")
                log_send_attempt(conn, customer_name, '', 
                               'No phone number available', 'skipped')
                skipped_count += 1
                continue
            
            # Format message - handle date from SQLite (could be string or date)
            expiry_date_str = str(visa_expiry_date)
            if isinstance(visa_expiry_date, date):
                expiry_date_str = visa_expiry_date.strftime('%Y-%m-%d')
            
            # Get today's date in UAE timezone
            today_date_str = datetime.now(UAE_TZ).strftime('%Y-%m-%d')
            
            message = FIXED_TEMPLATE.format(
                customer_name=customer_name,
                visa_type=visa_type,
                visa_expiry_date=expiry_date_str,
                today_date=today_date_str
            )
            
            logger.info(f"Processing: {customer_name} ({full_phone})")
            
            # Send message
            success, status = send_whatsapp_message(full_phone, message)
            
            # Log the attempt
            log_send_attempt(conn, customer_name, full_phone, message, status)
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
            
            # Random delay between messages (6-8 seconds)
            if customer != customers[-1]:  # Don't delay after last customer
                delay = random.uniform(6, 8)
                logger.debug(f"Waiting {delay:.2f} seconds before next message...")
                time.sleep(delay)
        
        logger.info("=" * 60)
        logger.info(f"Notification process completed:")
        logger.info(f"  - Sent: {sent_count}")
        logger.info(f"  - Failed: {failed_count}")
        logger.info(f"  - Skipped: {skipped_count}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error in main process: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

