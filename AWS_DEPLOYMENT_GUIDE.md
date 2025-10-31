# AWS Deployment Guide for CRM Application

This guide walks you through deploying your CRM application on AWS EC2.

## Prerequisites

- AWS Account with EC2 access
- SSH key pair for EC2 instance access
- Basic knowledge of Linux commands

## Step 1: Launch EC2 Instance

1. **Go to AWS EC2 Console** → Launch Instance
2. **Choose Instance Type**: 
   - Minimum: `t2.micro` (free tier) or `t3.small` for better performance
   - Recommended: `t3.medium` or larger for production
3. **Choose AMI**: 
   - Select **Ubuntu Server 22.04 LTS** (or latest LTS)
4. **Key Pair**: 
   - Select or create a new key pair for SSH access
5. **Network Settings**: 
   - Configure Security Group:
     - **SSH (22)**: Your IP only
     - **HTTP (80)**: 0.0.0.0/0 (or your IP for testing)
     - **Custom TCP (8080)**: Your IP or 0.0.0.0/0 (for web app)
     - **Custom TCP (3000)**: 127.0.0.1 only (for WAHA, localhost only)
6. **Storage**: 
   - Minimum 20 GB (recommended 30 GB)
7. **Launch the instance**

## Step 2: Setup Database (Choose One Option)

### Option A: AWS RDS PostgreSQL (Recommended)

1. **Create RDS Instance**:
   - Go to AWS RDS Console → Create Database
   - Engine: PostgreSQL (latest stable version)
   - Template: Free tier (or Production)
   - DB Instance Identifier: `crm-db`
   - Master Username: `postgres`
   - Master Password: Set a strong password
   - DB Instance Class: `db.t3.micro` (free tier) or larger
   - Storage: 20 GB minimum
   - Publicly Accessible: **YES** (for now, or use VPC if in same VPC)
   - VPC Security Group: Create new or use default
   - Database Name: `crm_db`

2. **Configure Security Group**:
   - Allow inbound PostgreSQL (5432) from your EC2 security group

3. **Get Endpoint**: Note the RDS endpoint (e.g., `crm-db.xxxxx.us-east-1.rds.amazonaws.com`)

### Option B: PostgreSQL on EC2 (Same Instance)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres psql -c "CREATE DATABASE crm_db;"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

## Step 3: Connect to EC2 Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-public-ip
```

## Step 4: Install Dependencies on EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install -y python3 python3-pip python3-venv git

# Install PostgreSQL client (if using RDS)
sudo apt install -y postgresql-client

# Install Docker and Docker Compose (for WAHA)
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Log out and log back in for docker group to take effect
```

## Step 5: Setup Application Directory

```bash
# Create application directory
mkdir -p ~/crm-app
cd ~/crm-app

# Clone your repository or upload files
# Option 1: Clone from Git
git clone <your-repo-url> .

# Option 2: Upload files using SCP (from your local machine)
# scp -i your-key.pem -r * ubuntu@your-ec2-ip:~/crm-app/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 6: Setup Database Schema

```bash
# Connect to your database (RDS or local)
# Replace with your actual credentials

# For RDS:
psql -h your-rds-endpoint.rds.amazonaws.com -U postgres -d crm_db

# For local:
sudo -u postgres psql -d crm_db

# Run these SQL commands:
```

Create a file `schema.sql`:

```sql
-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    visa_type VARCHAR(100) NOT NULL,
    visa_expiry_date DATE NOT NULL,
    country_code VARCHAR(10),
    phone_number VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_name, visa_expiry_date)
);

-- Create send_logs table
CREATE TABLE IF NOT EXISTS send_logs (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255),
    phone VARCHAR(50),
    message TEXT,
    status VARCHAR(50),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_visa_expiry ON customers(visa_expiry_date);
CREATE INDEX IF NOT EXISTS idx_send_logs_sent_at ON send_logs(sent_at);
```

Then import it:

```bash
psql -h your-rds-endpoint.rds.amazonaws.com -U postgres -d crm_db < schema.sql
```

## Step 7: Configure Environment Variables

```bash
cd ~/crm-app
cp .env.example .env
nano .env
```

Update `.env` with your actual values:

```bash
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_NAME=crm_db
DB_USER=postgres
DB_PASS=your_actual_password
WAHA_URL=http://localhost:3000
WAHA_API_KEY=your_waha_api_key_here
WAHA_SESSION=default
FLASK_DEBUG=False
PORT=8080
```

**Important**: Keep `.env` secure and never commit it to Git!

## Step 8: Setup WAHA (WhatsApp HTTP API)

```bash
cd ~/crm-app

# Create docker-compose.yml for WAHA
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  waha:
    image: devlikeapro/waha-plus:latest
    container_name: waha
    ports:
      - "3000:3000"
    environment:
      - WHATSAPP_API_HOSTNAME=0.0.0.0
      - WHATSAPP_API_PORT=3000
    volumes:
      - ./waha-data:/app/.sessions
    restart: unless-started
EOF

# Start WAHA
docker-compose up -d

# Check logs to get API key
docker-compose logs waha | grep -i "api key"
# Or check: docker-compose logs waha

# Update .env with the API key from logs
```

## Step 9: Setup Systemd Service for Flask App

```bash
cd ~/crm-app

# Copy service file to systemd directory
sudo cp crm-app.service /etc/systemd/system/

# Edit the service file if needed (update paths, user)
sudo nano /etc/systemd/system/crm-app.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable crm-app

# Start the service
sudo systemctl start crm-app

# Check status
sudo systemctl status crm-app

# View logs
sudo journalctl -u crm-app -f
```

## Step 10: Setup Cron Job for Automated Notifications

```bash
cd ~/crm-app

# Create environment file for cron
sudo nano /etc/crm-cron.env

# Add your environment variables:
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_NAME=crm_db
DB_USER=postgres
DB_PASS=your_actual_password
WAHA_URL=http://localhost:3000
WAHA_API_KEY=your_waha_api_key
WAHA_SESSION=default

# Make send_notifications.py executable
chmod +x send_notifications.py

# Setup cron job
crontab -e

# Add this line (runs daily at 3:00 UTC = 7:00 AM UAE):
0 3 * * * . /etc/crm-cron.env && cd /home/ubuntu/crm-app && /home/ubuntu/crm-app/venv/bin/python3 send_notifications.py >> /var/log/crm-cron.log 2>&1
```

## Step 11: Configure Firewall (if needed)

```bash
# Ubuntu comes with ufw (Uncomplicated Firewall)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 8080/tcp  # Flask app
sudo ufw enable
```

## Step 12: Setup Reverse Proxy (Optional but Recommended)

For production, use Nginx as a reverse proxy:

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/crm-app
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your EC2 public IP

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/crm-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 13: Testing

1. **Test Flask App**:
   - Open browser: `http://your-ec2-public-ip:8080`
   - Or if using Nginx: `http://your-ec2-public-ip`

2. **Test Database Connection**:
   - Try adding a customer
   - Check if it appears in the list

3. **Test WAHA**:
   - Check if WAHA container is running: `docker ps`
   - Check WAHA logs: `docker-compose logs waha`

4. **Test Cron Job**:
   - Run manually: `cd ~/crm-app && source venv/bin/activate && python3 send_notifications.py`
   - Check logs: `tail -f /var/log/crm-cron.log`

## Step 14: Security Hardening

1. **Use AWS Secrets Manager** for sensitive credentials instead of `.env` file
2. **Enable SSL/TLS** using Let's Encrypt (for production domains)
3. **Restrict Security Groups** to specific IPs
4. **Regular Updates**: `sudo apt update && sudo apt upgrade`
5. **Use IAM Roles** for database access (instead of passwords in .env)

## Troubleshooting

### Application not starting:
```bash
sudo journalctl -u crm-app -n 50
```

### Database connection issues:
- Check security groups allow port 5432
- Verify credentials in `.env`
- Test connection: `psql -h your-db-host -U postgres -d crm_db`

### WAHA not working:
```bash
docker-compose logs waha
docker-compose restart waha
```

### Cron job not running:
- Check cron logs: `grep CRON /var/log/syslog`
- Verify script is executable
- Check environment variables are loaded

## Maintenance Commands

```bash
# View application logs
sudo journalctl -u crm-app -f

# Restart application
sudo systemctl restart crm-app

# View cron logs
tail -f /var/log/crm-cron.log

# Update application code
cd ~/crm-app
git pull  # if using git
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart crm-app
```

## Next Steps

1. **Domain Setup**: Point your domain to EC2 IP
2. **SSL Certificate**: Setup Let's Encrypt SSL
3. **Backup Strategy**: Setup automated RDS backups
4. **Monitoring**: Setup CloudWatch alarms
5. **Auto-scaling**: Configure auto-scaling if needed

