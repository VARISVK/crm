# Railway Deployment Guide for CRM App

## Overview
This guide deploys your CRM on Railway with:
- Flask web app
- WAHA WhatsApp API (Docker)
- Scheduled notifications (via external cron service)

## Prerequisites
- Railway account (free tier available)
- GitHub repository connected
- WhatsApp account for WAHA

---

## Step 1: Setup Railway Account

1. **Go to:** https://railway.app
2. **Sign up** with GitHub
3. **Create new project**

---

## Step 2: Deploy Flask App

1. **Click "New Project" → "Deploy from GitHub repo"**
2. **Select your repo:** `VARISVK/crm`
3. **Railway auto-detects Python**
4. **Configure:**
   - **Root Directory:** Leave empty (or `.` if needed)
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. **Environment Variables:**
   ```
   PORT=8080
   WAHA_URL=http://waha:3000
   WAHA_API_KEY=your_api_key_here
   WAHA_SESSION=default
   DB_PATH=./crm.db
   FLASK_DEBUG=False
   ```
6. **Click "Deploy"**

---

## Step 3: Deploy WAHA Service

1. **In same project, click "New" → "GitHub Repo"**
2. **Select same repo:** `VARISVK/crm`
3. **Configure:**
   - **Service Type:** Docker
   - **Dockerfile:** `Dockerfile.waha`
   - **Root Directory:** `.`
4. **Environment Variables:**
   ```
   WHATSAPP_API_HOSTNAME=0.0.0.0
   WHATSAPP_API_PORT=3000
   ```
5. **Click "Deploy"**

---

## Step 4: Setup Service Communication

Railway services in the same project can communicate using:
- **Internal:** Use service name (e.g., `http://waha:3000`)
- **External:** Use public URL

**Update Flask app env vars:**
1. Go to Flask service → Variables
2. Set `WAHA_URL` to WAHA service's internal URL
3. Or use the public URL if internal doesn't work

---

## Step 5: Initialize Database

1. **Go to Flask service → Deployments → Select latest**
2. **Click "View Logs"**
3. **Or use Railway CLI:**
   ```bash
   railway run python3 init_db.py
   ```

---

## Step 6: Setup Scheduled Notifications

Railway doesn't have built-in cron, so we'll use **external cron service**:

### Option A: cron-job.org (Free)

1. **Go to:** https://cron-job.org (free tier available)
2. **Create account**
3. **Create new cron job:**
   - **URL:** `https://your-crm-app.railway.app/api/trigger-notifications`
   - **Schedule:** Every day at 3:00 AM UTC
   - **HTTP Method:** GET or POST

### Option B: Create API Endpoint (Better)

Add this to your Flask app to trigger notifications manually or via HTTP:

```python
@app.route('/api/trigger-notifications', methods=['POST', 'GET'])
def trigger_notifications():
    """API endpoint to trigger notifications manually or via cron."""
    import subprocess
    result = subprocess.run(['python3', 'send_notifications.py'], 
                          capture_output=True, text=True)
    return jsonify({
        'success': result.returncode == 0,
        'output': result.stdout,
        'error': result.stderr
    })
```

Then use cron-job.org to call this endpoint.

### Option C: GitHub Actions (Free)

Create `.github/workflows/cron.yml`:
```yaml
name: Daily Notifications
on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM UTC = 7 AM UAE
  workflow_dispatch:  # Allow manual trigger

jobs:
  send-notifications:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run notifications
        env:
          WAHA_URL: ${{ secrets.WAHA_URL }}
          WAHA_API_KEY: ${{ secrets.WAHA_API_KEY }}
          WAHA_SESSION: default
          DB_PATH: ./crm.db
        run: |
          # Download DB from Railway or use API
          python3 send_notifications.py
```

---

## Step 7: Get WAHA API Key

1. **Go to WAHA service → View Logs**
2. **Look for:**
   ```
   WAHA_DASHBOARD_USERNAME=admin
   WAHA_DASHBOARD_PASSWORD=xxxxx
   ```
3. **Access WAHA dashboard** (public URL)
4. **Login and get API key**

---

## Step 8: Connect WhatsApp

1. **Open WAHA public URL**
2. **Login with credentials from logs**
3. **Create session**
4. **Scan QR code with WhatsApp**

---

## Railway Free Tier

- **$5 credit monthly** (free)
- **Pay-as-you-go** after credit used
- **No sleep time** (services stay up)
- **Better than Render** for free tier

---

## Troubleshooting

### Services can't communicate
- Use internal service URLs: `http://waha:3000`
- Check service names match
- Verify environment variables

### Database issues
- Run `init_db.py` via Railway CLI
- Check DB_PATH is correct
- Database persists in Railway's volume

### Cron not working
- Use cron-job.org as external service
- Or use GitHub Actions
- Or create manual trigger endpoint

---

## Cost Estimate

- **Flask App:** ~$0-5/month (within free credit)
- **WAHA Service:** ~$0-5/month (within free credit)
- **Cron Service:** Free (external)
- **Total:** Free (with $5 monthly credit)

