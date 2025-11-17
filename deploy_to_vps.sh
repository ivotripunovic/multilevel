#!/usr/bin/env bash
# Minimal deploy script to set up this Django project on a Linux VPS (Ubuntu/Debian).
# Usage (run as root or with sudo on the VPS):
#   sudo bash deploy_to_vps.sh <git_repo_url> <project_name> <domain> [wsgi_module]
# Example:
#   sudo bash deploy_to_vps.sh git@github.com:your/repo.git mysite example.com hello_world.wsgi:application
set -euo pipefail

REPO_URL="${1:-}"
PROJECT_NAME="${2:-myproject}"
DOMAIN="${3:-example.com}"
WSGI_APP="${4:-hello_world.wsgi:application}"   # module:path
APP_USER="${APP_USER:-www-data}"
BASE_DIR="/opt/${PROJECT_NAME}"
VENV_DIR="${BASE_DIR}/venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
GUNICORN_SOCK="/run/gunicorn_${PROJECT_NAME}.sock"
SYSTEMD_SERVICE="/etc/systemd/system/${PROJECT_NAME}.service"
NGINX_CONF="/etc/nginx/sites-available/${PROJECT_NAME}"
STATIC_ROOT="${BASE_DIR}/staticfiles"
ENV_FILE="${BASE_DIR}/.env"

if [ -z "$REPO_URL" ]; then
  echo "Usage: sudo bash $0 <git_repo_url> <project_name> <domain> [wsgi_module]"
  exit 2
fi

echo "Deploying ${PROJECT_NAME} from ${REPO_URL} to ${BASE_DIR} (domain: ${DOMAIN})"

# 1. Install system packages
apt update
apt install -y git "${PYTHON_BIN}" "${PYTHON_BIN}-venv" build-essential nginx

# 2. Create app user (if not using existing)
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}" || true
fi

# 3. Clone project (or pull if exists)
if [ -d "${BASE_DIR}/.git" ]; then
  echo "Existing repo found, pulling latest"
  cd "${BASE_DIR}"
  git fetch --all
  git reset --hard origin/HEAD
else
  rm -rf "${BASE_DIR}"
  mkdir -p "${BASE_DIR}"
  chown "${APP_USER}:${APP_USER}" "${BASE_DIR}"
  git clone "${REPO_URL}" "${BASE_DIR}"
fi

# 4. Create virtualenv and install requirements
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
# Ensure pip up-to-date
"${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel
if [ -f "${BASE_DIR}/requirements.txt" ]; then
  "${VENV_DIR}/bin/pip" install -r "${BASE_DIR}/requirements.txt"
else
  echo "Warning: requirements.txt not found in repo root"
fi

# 5. Create .env (non-production safe defaults) and apply permissive ownership
SECRET_KEY="$(tr -dc 'A-Za-z0-9!@#$%^&*()_+-=' < /dev/urandom | head -c 48 || echo 'dev-secret')"
cat > "${ENV_FILE}" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN}
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=db.sqlite3
DB_USERNAME=
DB_PASSWORD=
EOF
chown "${APP_USER}:${APP_USER}" "${ENV_FILE}"
chmod 600 "${ENV_FILE}"

# 6. Run migrations & collectstatic
cd "${BASE_DIR}"
# Ensure manage.py executable uses venv python
"${VENV_DIR}/bin/python" manage.py migrate --noinput
mkdir -p "${STATIC_ROOT}"
"${VENV_DIR}/bin/python" manage.py collectstatic --noinput --clear --settings=hello_world.settings
chown -R "${APP_USER}:${APP_USER}" "${BASE_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${STATIC_ROOT}"

# 7. Create systemd service for gunicorn
cat > "${SYSTEMD_SERVICE}" <<EOF
[Unit]
Description=gunicorn daemon for ${PROJECT_NAME}
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${BASE_DIR}
Environment=PATH=${VENV_DIR}/bin
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn --workers 3 --bind unix:${GUNICORN_SOCK} ${WSGI_APP}

Restart=always

[Install]
WantedBy=multi-user.target
EOF

# create socket directory and set permissions
mkdir -p "$(dirname "${GUNICORN_SOCK}")"
chown "${APP_USER}:${APP_USER}" "$(dirname "${GUNICORN_SOCK}")"

systemctl daemon-reload
systemctl enable --now "${PROJECT_NAME}.service"

# 8. Configure nginx to proxy to the socket and serve static files
cat > "${NGINX_CONF}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    client_max_body_size 100M;

    location /static/ {
        alias ${STATIC_ROOT}/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:${GUNICORN_SOCK};
    }
}
EOF

ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/${PROJECT_NAME}
nginx -t
systemctl restart nginx

echo "Deployment complete."
echo "Project directory: ${BASE_DIR}"
echo "Gunicorn service: ${PROJECT_NAME}.service"
echo "Nginx site: ${NGINX_CONF}"
echo "Open site in browser with: \$BROWSER http://${DOMAIN}"