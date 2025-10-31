-- CRM Database Schema for SQLite3
-- Run this SQL script to create the required tables

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    visa_type TEXT NOT NULL,
    visa_expiry_date DATE NOT NULL,
    country_code TEXT,
    phone_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_name, visa_expiry_date)
);

-- Create send_logs table
CREATE TABLE IF NOT EXISTS send_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    phone TEXT,
    message TEXT,
    status TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_visa_expiry ON customers(visa_expiry_date);
CREATE INDEX IF NOT EXISTS idx_send_logs_sent_at ON send_logs(sent_at);
