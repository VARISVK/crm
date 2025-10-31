# AWS Deployment Checklist

Use this checklist to ensure you complete all steps for deploying your CRM on AWS.

## Pre-Deployment

- [ ] AWS Account set up
- [ ] EC2 key pair created/downloaded
- [ ] AWS RDS PostgreSQL instance planned (or PostgreSQL on EC2)
- [ ] Domain name ready (optional, for production)

## EC2 Setup

- [ ] Launch EC2 instance (Ubuntu 22.04 LTS)
- [ ] Configure Security Group:
  - [ ] SSH (22) - Your IP
  - [ ] HTTP (80) - Your IP or 0.0.0.0/0
  - [ ] Custom TCP (8080) - Your IP or 0.0.0.0/0
  - [ ] Custom TCP (3000) - 127.0.0.1 only (WAHA)
- [ ] Note EC2 public IP address

## Database Setup

- [ ] Create RDS PostgreSQL instance (recommended) OR install PostgreSQL on EC2
- [ ] Create database `crm_db`
- [ ] Set database password
- [ ] Configure security group to allow EC2 access
- [ ] Test database connection from EC2
- [ ] Run `schema.sql` to create tables

## Application Setup on EC2

- [ ] SSH into EC2 instance
- [ ] Install system dependencies (Python, Docker, etc.)
- [ ] Create application directory `/home/ubuntu/crm-app`
- [ ] Upload/copy application files
- [ ] Create Python virtual environment
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Copy `env.template` to `.env`
- [ ] Configure `.env` with actual credentials
- [ ] Test database connection from Python

## WAHA Setup

- [ ] Install Docker and Docker Compose
- [ ] Copy `docker-compose.yml` to application directory
- [ ] Start WAHA: `docker-compose up -d`
- [ ] Check WAHA logs for API key
- [ ] Update `.env` with WAHA API key
- [ ] Verify WAHA is accessible on port 3000

## Flask Application Service

- [ ] Copy `crm-app.service` to `/etc/systemd/system/`
- [ ] Update paths in service file if needed
- [ ] Reload systemd: `sudo systemctl daemon-reload`
- [ ] Enable service: `sudo systemctl enable crm-app`
- [ ] Start service: `sudo systemctl start crm-app`
- [ ] Check status: `sudo systemctl status crm-app`
- [ ] View logs: `sudo journalctl -u crm-app -f`

## Cron Job Setup

- [ ] Make `send_notifications.py` executable
- [ ] Create environment file `/etc/crm-cron.env` with credentials
- [ ] Setup crontab: `crontab -e`
- [ ] Add cron job (runs at 3:00 UTC = 7:00 AM UAE daily)
- [ ] Test cron script manually
- [ ] Check cron logs: `tail -f /var/log/crm-cron.log`

## Testing

- [ ] Access web app in browser: `http://your-ec2-ip:8080`
- [ ] Add a test customer
- [ ] Verify customer appears in list
- [ ] Import Excel file (test)
- [ ] Check database for new records
- [ ] Verify WAHA connection (check Docker logs)
- [ ] Test notification script manually

## Security

- [ ] `.env` file has correct permissions (not world-readable)
- [ ] Security groups restricted to necessary IPs
- [ ] Database credentials are strong
- [ ] WAHA API key is secure
- [ ] Firewall (ufw) configured if needed

## Optional Production Setup

- [ ] Install and configure Nginx reverse proxy
- [ ] Setup SSL certificate (Let's Encrypt)
- [ ] Configure domain name DNS
- [ ] Setup automated backups for RDS
- [ ] Configure CloudWatch monitoring
- [ ] Setup log rotation

## Post-Deployment

- [ ] Monitor application logs for 24 hours
- [ ] Verify cron job runs successfully
- [ ] Test end-to-end: Add customer → Wait for expiry → Check notification
- [ ] Document any custom configurations
- [ ] Create backup of `.env` file (securely stored)

## Troubleshooting Reference

If something doesn't work:

1. **App not accessible**: Check security groups, service status, firewall
2. **Database errors**: Verify credentials, security groups, network access
3. **WAHA not working**: Check Docker logs, port binding, API key
4. **Cron not running**: Check cron logs, file permissions, environment variables
5. **Service crashes**: Check systemd logs: `sudo journalctl -u crm-app -n 50`

## Quick Commands Reference

```bash
# Service management
sudo systemctl status crm-app
sudo systemctl restart crm-app
sudo journalctl -u crm-app -f

# WAHA management
docker-compose ps
docker-compose logs waha
docker-compose restart waha

# Database connection test
psql -h your-db-host -U postgres -d crm_db

# Manual cron test
cd ~/crm-app
source venv/bin/activate
python3 send_notifications.py

# View logs
tail -f /var/log/crm-app-error.log
tail -f /var/log/crm-cron.log
```

