#!/usr/bin/env bash
# deploy.sh — Run on a fresh Vultr Ubuntu 22.04 Cloud Compute instance
# Usage:  bash deploy.sh
set -euo pipefail

GITHUB_USER="AlbertNjobo"
REPO_URL="https://github.com/${GITHUB_USER}/sentinel-api.git"
APP_DIR="/opt/sentinel-api"
SERVICE_USER="sentinel"

echo "==> [1/7] System update"
apt-get update -q && apt-get upgrade -yq

echo "==> [2/7] Install system packages"
apt-get install -yq python3 python3-pip python3-venv git nginx ufw

echo "==> [3/7] Create dedicated service user"
id "$SERVICE_USER" &>/dev/null || useradd -r -s /usr/sbin/nologin "$SERVICE_USER"

echo "==> [4/7] Clone / pull repo"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

echo "==> [5/7] Python virtualenv + dependencies"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

echo "==> [6/7] systemd service"
cp "$APP_DIR/scripts/sentinel-api.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable sentinel-api
systemctl restart sentinel-api
systemctl status sentinel-api --no-pager

echo "==> [7/7] Nginx + firewall"
cp "$APP_DIR/scripts/nginx-sentinel.conf" /etc/nginx/sites-available/sentinel
ln -sf /etc/nginx/sites-available/sentinel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

ufw allow OpenSSH
ufw allow 'Nginx HTTP'
ufw --force enable

# Get public IP (Vultr metadata service)
VULTR_IP=$(curl -sf http://169.254.169.254/latest/meta-data/public-ipv4 \
           || hostname -I | awk '{print $1}')

echo ""
echo "✅  Sentinel API is live!"
echo ""
echo "   Swagger UI  →  http://${VULTR_IP}/docs"
echo "   Health      →  http://${VULTR_IP}/health"
echo "   Metrics     →  http://${VULTR_IP}/metrics"
echo "   Alerts      →  http://${VULTR_IP}/alerts"
echo ""
echo "   To add HTTPS:"
echo "   apt install certbot python3-certbot-nginx -y"
echo "   certbot --nginx -d yourdomain.com"
