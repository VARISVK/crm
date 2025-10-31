# Quick Deployment Guide

## For Local/Development Deployment

### 1. Initialize Database (First Time Only)
```bash
python3 init_db.py
```
This creates `crm.db` in your project directory.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python3 app.py
```
Access at: `http://localhost:8080`

### 4. Setup WAHA (WhatsApp API)
```bash
# Start WAHA using Docker
docker-compose up -d

# Check logs to get API key
docker-compose logs waha | grep -i "api key"
```

### 5. Configure Environment (Optional)
Create `.env` file or set environment variables:
```bash
WAHA_URL=http://localhost:3000
WAHA_API_KEY=your_waha_api_key_here
WAHA_SESSION=default
```

### 6. Test Notification Script Manually
```bash
python3 send_notifications.py
```

### 7. Setup Cron Job (For Automated Daily Notifications)
```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 3:00 UTC = 7:00 AM UAE):
0 3 * * * cd /path/to/your/project && /usr/bin/python3 send_notifications.py >> /var/log/crm-cron.log 2>&1
```

**Note for Windows:** Cron doesn't exist on Windows. Use Task Scheduler or run manually.

---

## For AWS EC2 Deployment

Follow the detailed guide in `AWS_DEPLOYMENT_GUIDE.md` or see quick steps below:

### Quick Steps:
1. **Launch EC2** (Ubuntu 22.04)
2. **SSH into instance**
3. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv git docker.io docker-compose
   ```
4. **Clone/Upload your code** to `/home/ubuntu/crm-app`
5. **Setup virtual environment:**
   ```bash
   cd ~/crm-app
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
6. **Initialize database:**
   ```bash
   python3 init_db.py
   ```
7. **Start WAHA:**
   ```bash
   docker-compose up -d
   ```
8. **Setup systemd service** (see `crm-app.service`)
9. **Setup cron job** (see `crm-cron`)
10. **Access app** at `http://your-ec2-ip:8080`

---

## Checklist Before Deploying:

- [ ] Database initialized (`crm.db` exists)
- [ ] Dependencies installed
- [ ] WAHA running and API key obtained
- [ ] `.env` configured (or environment variables set)
- [ ] Tested adding a customer manually
- [ ] Tested notification script manually
- [ ] Cron job configured (for automated sending)
- [ ] Firewall/security groups configured (if on cloud)

---

## Important Notes:

1. **Database:** SQLite database (`crm.db`) will be created automatically in project directory
2. **WAHA:** Must be running before sending notifications
3. **Timezone:** All dates are handled in UAE timezone (Asia/Dubai)
4. **Notifications:** Run daily at **7:00 AM UAE time** (3:00 AM UTC)
5. **Logs:** Check `/var/log/crm-cron.log` for cron job logs

