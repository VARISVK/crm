# Render Deployment Guide for CRM App

## Overview
This guide walks you through deploying your CRM application on Render with:
- Flask web app
- WAHA WhatsApp API service
- Automated daily notifications (cron job)

## Prerequisites
- Render account (free tier available)
- GitHub repository with your code
- WhatsApp account for WAHA connection

---

## Step 1: Prepare Your Repository

Your code is already on GitHub at: `https://github.com/VARISVK/crm`

---

## Step 2: Deploy Services on Render

### Option A: Using render.yaml (Recommended - Automated)

1. **Go to Render Dashboard:** https://dashboard.render.com
2. **Click "New" → "Blueprint"**
3. **Connect your GitHub repository:** `VARISVK/crm`
4. **Render will automatically detect `render.yaml`**
5. **Click "Apply"**
6. **Set Environment Variables:**
   - `WAHA_API_KEY` - Get this from WAHA logs after deployment

### Option B: Manual Setup (Step by Step)

#### 2.1. Deploy WAHA Service First

1. **Go to Render Dashboard → "New" → "Web Service"**
2. **Connect your GitHub repository:** `VARISVK/crm`
3. **Configure:**
   - **Name:** `waha`
   - **Region:** Choose closest to you
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Environment:** `Docker`
   - **Dockerfile Path:** `Dockerfile.waha`
   - **Docker Context:** `.`
4. **Environment Variables:**
   ```
   WHATSAPP_API_HOSTNAME=0.0.0.0
   WHATSAPP_API_PORT=3000
   ```
5. **Click "Create Web Service"**
6. **Wait for deployment**
7. **Note the WAHA URL** (e.g., `https://waha-xxxx.onrender.com`)

#### 2.2. Deploy Flask App

1. **Go to "New" → "Web Service"**
2. **Connect GitHub repository:** `VARISVK/crm`
3. **Configure:**
   - **Name:** `crm-app`
   - **Region:** Same as WAHA
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. **Environment Variables:**
   ```
   PORT=8080
   WAHA_URL=http://waha:3000
   WAHA_API_KEY=your_api_key_here
   WAHA_SESSION=default
   FLASK_DEBUG=False
   DB_PATH=/opt/render/project/src/crm.db
   ```
   **Note:** Get `WAHA_API_KEY` from WAHA service logs after it deploys
5. **Click "Create Web Service"**

#### 2.3. Initialize Database

1. **Go to your Flask app service**
2. **Click "Shell" tab**
3. **Run:**
   ```bash
   python3 init_db.py
   ```

#### 2.4. Setup Scheduled Notifications (Cron Job)

1. **Go to "New" → "Cron Job"**
2. **Configure:**
   - **Name:** `send-notifications`
   - **Region:** Same as other services
   - **Branch:** `main`
   - **Root Directory:** Leave empty
   - **Schedule:** `0 3 * * *` (3 AM UTC = 7 AM UAE)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 send_notifications.py`
3. **Environment Variables:**
   ```
   WAHA_URL=http://waha:3000
   WAHA_API_KEY=your_api_key_here
   WAHA_SESSION=default
   DB_PATH=/opt/render/project/src/crm.db
   ```
4. **Click "Create Cron Job"**

---

## Step 3: Get WAHA API Key

1. **Go to WAHA service**
2. **Click "Logs" tab**
3. **Look for lines like:**
   ```
   WAHA_DASHBOARD_USERNAME=admin
   WAHA_DASHBOARD_PASSWORD=xxxxx
   ```
4. **Or access WAHA web interface:**
   - Go to WAHA service URL (e.g., `https://waha-xxxx.onrender.com`)
   - Login with credentials from logs
   - Check API/Keys section for API key

---

## Step 4: Configure Environment Variables

Update environment variables in all services:
1. **Flask App** → Environment → Add `WAHA_API_KEY`
2. **Cron Job** → Environment → Add `WAHA_API_KEY`

---

## Step 5: Connect WhatsApp

1. **Access WAHA dashboard:** Your WAHA service URL
2. **Login with credentials from logs**
3. **Create/Start a session**
4. **Scan QR code with WhatsApp**
5. **Wait for connection**

---

## Step 6: Test

1. **Access your Flask app:** `https://crm-app-xxxx.onrender.com`
2. **Add a test customer**
3. **Test notification manually** (run cron script in Shell)

---

## Important Notes

### Service Communication
- **For services to communicate:** Use internal service names
- **WAHA URL:** `http://waha:3000` (internal) OR `https://waha-xxxx.onrender.com` (external)
- **Test which works:** Try both in your env vars

### Database
- **SQLite on Render:** Persists as long as service is running
- **For production:** Consider Render PostgreSQL (free tier available)
- **Database location:** `/opt/render/project/src/crm.db`

### Free Tier Limitations
- Services may sleep after 15 minutes of inactivity
- First request may be slow (wake-up time)
- Consider paid plan for 24/7 uptime

### Cron Job Schedule
- **Format:** `0 3 * * *` = 3 AM UTC daily = 7 AM UAE time
- **To change:** Edit cron job schedule in Render dashboard

---

## Troubleshooting

### WAHA can't be reached
- Check WAHA service is running
- Verify environment variables
- Check service URLs in logs

### Database errors
- Run `init_db.py` in Shell
- Check DB_PATH environment variable
- Ensure database file exists

### Cron job not running
- Check cron job logs
- Verify environment variables
- Check schedule format

### Services not communicating
- Use internal service URLs (`http://waha:3000`)
- Or use external URLs with proper networking

---

## Next Steps

1. **Monitor logs** for any errors
2. **Test adding customers** through web interface
3. **Test notifications** by running script manually
4. **Verify cron job** runs at scheduled time
5. **Set up monitoring** (optional)

---

## Cost Estimate (Free Tier)
- **3 Web Services:** Free (with limitations)
- **1 Cron Job:** Free
- **Total:** Free (with 15-min sleep time)

For 24/7 uptime, consider Render's paid plans ($7-25/month per service).

