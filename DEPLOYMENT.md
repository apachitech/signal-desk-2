# SignalDesk — Complete Live Production Deployment Guide

This guide walks you through deploying **SignalDesk** online so traders worldwide can access the live terminal, real-time confluence signals, backtester, and Pocket Option guides 24/7.

---

## Deployment Platform Comparison

Choose the method that best fits your technical experience and budget:

| Platform | Best For | Setup Time | Cost | Free SSL (`https://`) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Vercel** *(Ultra-Popular & Free)* | Serverless, Edge CDN, 1-click Git import | **2 Minutes** | **100% Free** | ✅ Included automatically |
| **2. Netlify** *(Free Global CDN + Serverless)* | Static CDN + Python Lambda Functions | **2 Minutes** | **100% Free** | ✅ Included automatically |
| **3. Render.com** *(Best Persistent Host)* | Zero server maintenance, continuous background | **3 Minutes** | **Free tier** ($7/mo for 24/7 non-sleep) | ✅ Included automatically |
| **4. Railway.app** | Modern 1-click GitHub sync | **3 Minutes** | $5/mo credit trial | ✅ Included automatically |
| **5. Ubuntu VPS (DigitalOcean / Hetzner)** | High-concurrency, institutional 24/7 uptime | **10 Minutes** | **$4 – $6 / month** | ✅ Free via Let's Encrypt |
| **6. Docker / Docker Compose** | Portable containerization on any cloud | **2 Minutes** | Depends on host | ✅ Via Traefik / Nginx |

---

## Method 1: Deploy on Vercel (Serverless Edge)

**Yes, you can absolutely deploy SignalDesk on Vercel!** The repository is pre-configured with:
- **`vercel.json`**: Rewrites all web traffic to the serverless ASGI application.
- **`api/index.py`**: The serverless entrypoint connecting FastAPI to Vercel's Python runtime.

### Option A: Deploy via GitHub (1-Click Web Interface)
1. Push your project to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Deploy SignalDesk to Vercel"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/signal-desk.git
   git push -u origin main
   ```
2. Go to [Vercel.com](https://vercel.com) and log in with your GitHub account.
3. Click **Add New...** $\rightarrow$ **Project**.
4. Import your `signal-desk` repository.
5. In the **Configure Project** screen:
   - **Framework Preset:** Leave as *Other*.
   - **Root Directory:** `./`
   - **Build and Output Settings:** Leave default (Vercel reads `vercel.json` automatically).
6. Click **Deploy**.
7. In ~60 seconds, your site will be live at:
   `https://signal-desk-yourname.vercel.app`

### Option B: Deploy via Vercel CLI (From your Terminal)
1. Install Vercel CLI globally (if you have Node.js):
   ```bash
   npm install -g vercel
   ```
2. Inside your `signal-desk-2` folder, run:
   ```bash
   vercel
   ```
3. Follow the on-screen prompts (accept defaults). When ready for production, run:
   ```bash
   vercel --prod
   ```

### 💡 What to Know About Vercel (Serverless vs Dedicated Server)
- **Edge CDN Speed:** Vercel serves the HTML, CSS, JavaScript, and TradingView charts from edge data centers closest to the user with instant loading.
- **Serverless Lifecyle:** Vercel puts Python functions to sleep when no requests are being made. The first request after a period of inactivity may take 1–2 seconds (cold start), but as soon as the trader starts streaming signals, it stays warm and responsive.
- **For Non-Stop 24/7 Dedicated Server:** If you prefer a continuously running process without any cold starts, use **Render (Method 3)** or a **VPS (Method 5)**.

---

## Method 2: Deploy on Netlify (Global CDN + Serverless Functions)

**Netlify is also 100% supported!** The repository includes:
- **`netlify.toml`**: Configures Netlify's build, static publishing directory, and API proxy rewrites.
- **`netlify/functions/api.py`**: Uses **Mangum** (AWS Lambda / Netlify ASGI adapter) to run FastAPI serverless endpoints.
- **`requirements.txt`**: Includes `mangum` alongside FastAPI, pandas, and yfinance.

### Option A: Deploy via GitHub (1-Click Web Interface)
1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Deploy SignalDesk to Netlify"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/signal-desk.git
   git push -u origin main
   ```
2. Go to [Netlify.com](https://www.netlify.com) and log in with GitHub.
3. Click **Add new site** $\rightarrow$ **Import an existing project**.
4. Select **GitHub** and choose your `signal-desk` repository.
5. Netlify will automatically detect `netlify.toml`:
   - **Publish directory:** `static`
   - **Functions directory:** `netlify/functions`
6. Click **Deploy signal-desk**.
7. Your terminal will be live in 1–2 minutes at:
   `https://your-custom-name.netlify.app`

### Option B: Deploy via Netlify CLI (Terminal)
1. Install the Netlify CLI:
   ```bash
   npm install -g netlify-cli
   ```
2. Authenticate:
   ```bash
   netlify login
   ```
3. Deploy to production:
   ```bash
   netlify deploy --prod
   ```

### 💡 Why Netlify is Great for SignalDesk:
- **Lightning-Fast Static CDN:** Your HTML, CSS, JavaScript, icons, and TradingView charts are cached across worldwide Netlify Edge nodes for instant 50ms initial page load.
- **Auto SSL:** Free Let's Encrypt certificate generated immediately.
- **Custom Domains:** 1-click domain linking (`signals.yourbrand.com`).

---

## Method 3: Deploy on Render.com (Continuous Web Service)

Render is the simplest cloud platform to deploy FastAPI applications with an automatic free SSL certificate.

### Step 1: Push your Code to GitHub
1. Create a free account on [GitHub.com](https://github.com) if you haven't already.
2. Initialize and push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial SignalDesk commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/signal-desk.git
   git push -u origin main
   ```

### Step 2: Create a Web Service on Render
1. Go to [Render.com](https://render.com) and sign in with GitHub.
2. Click **New +** in the top navigation and select **Web Service**.
3. Choose **Build and deploy from a Git repository** $\rightarrow$ Click **Next**.
4. Select your `signal-desk` repository.

### Step 3: Configure Settings
Fill in the following fields:
- **Name:** `signaldesk` (or your preferred name)
- **Region:** Frankfurt (EU) or Oregon (US) — *choose closest to your primary user base*
- **Branch:** `main`
- **Root Directory:** *(leave blank)*
- **Runtime:** `Python 3`
- **Build Command:**
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Plan:** Choose **Free** or **Starter ($7/mo)** *(Starter prevents the service from spinning down during periods of inactivity)*.

### Step 4: Deploy & Live Interaction
1. Click **Create Web Service**.
2. Render will build dependencies and launch your application.
3. Within 60–90 seconds, your site will be live at:
   `https://signaldesk.onrender.com`
4. Anyone on the internet can now open this link on their mobile device or desktop to trade with live confluence signals!

---

## Method 4: Deploy on Railway.app

Railway offers instant zero-config deployments directly from Git repositories.

1. Go to [Railway.app](https://railway.app) and sign in with GitHub.
2. Click **New Project** $\rightarrow$ Select **Deploy from GitHub repo**.
3. Pick your `signal-desk` repository.
4. Railway will automatically detect the `Procfile` and `requirements.txt`.
5. Under **Settings** $\rightarrow$ **Networking**, click **Generate Domain**.
6. Your live URL will appear immediately (e.g., `https://signal-desk-production.up.railway.app`).

---

## Method 5: Production VPS Deployment (Ubuntu 22.04 / 24.04 LTS)

For maximum performance, sub-millisecond signal generation, and handling thousands of simultaneous traders, a Linux VPS (DigitalOcean Droplet, Hetzner Cloud, Linode, or AWS EC2) is the industry standard.

### Step 1: Connect to your Server
```bash
ssh root@YOUR_SERVER_IP
```

### Step 2: Install System Dependencies
```bash
apt update && apt upgrade -y
apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx ufw
```

### Step 3: Configure Firewall (Security)
```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

### Step 4: Clone the Codebase & Setup Python Virtual Environment
```bash
cd /var/www
git clone https://github.com/YOUR_USERNAME/signal-desk.git
cd signal-desk

# Create isolated Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Create a Systemd Service (Auto-Restart on Crash or Reboot)
Create `/etc/systemd/system/signaldesk.service`:
```bash
nano /etc/systemd/system/signaldesk.service
```

Paste the following configuration:
```ini
[Unit]
Description=SignalDesk Trading Terminal Application
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/signal-desk
Environment="PATH=/var/www/signal-desk/venv/bin"
Environment="HOST=127.0.0.1"
Environment="PORT=8000"
ExecStart=/var/www/signal-desk/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
systemctl daemon-reload
systemctl enable signaldesk
systemctl start signaldesk
systemctl status signaldesk
```

### Step 6: Configure Nginx Reverse Proxy
Create `/etc/nginx/sites-available/signaldesk`:
```bash
nano /etc/nginx/sites-available/signaldesk
```

Paste the following Nginx block (replace `yourdomain.com` with your real domain or IP):
```nginx
server {
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
}
```

Enable the site and reload Nginx:
```bash
ln -s /etc/nginx/sites-available/signaldesk /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Step 7: Enable 100% Free HTTPS with Let's Encrypt
```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
*Select option to redirect HTTP traffic to HTTPS automatically.*

Your SignalDesk Terminal is now running in high-performance production mode with enterprise-grade SSL!

---

## Method 6: 1-Command Docker Deployment

If you prefer containerized deployment, pre-configured `Dockerfile` and `docker-compose.yml` files are included in the repository.

1. Ensure Docker and Docker Compose are installed on your server:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
2. Build and run in background:
   ```bash
   docker compose up -d --build
   ```
3. Check container status:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

---

## Connecting a Custom Domain (e.g., `trade.yourbrand.com`)

1. Buy a domain on **Namecheap**, **GoDaddy**, or **Cloudflare**.
2. Create a DNS Record:
   - **Type:** `A` Record
   - **Name:** `@` (or `signals` for a subdomain like `signals.yourbrand.com`)
   - **Value:** Your Server IP (or the CNAME provided by Render/Railway).
3. If using Cloudflare:
   - Enable the Orange Cloud (Proxy mode) for free DDoS protection, SSL encryption, and global CDN asset caching.

---

## Production Optimization Checklist

Before sending paid traffic or thousands of users to your terminal:

- [x] **Lightweight Chart CDN**: TradingView Lightweight Charts is already loaded via high-speed unpkg CDN.
- [ ] **Multi-Worker Scaling**: For VPS deployments, use `--workers 4` (or `2 * CPU cores + 1`) in your Uvicorn command to process parallel API queries simultaneously.
- [ ] **Automated Code Updates**:
  To deploy updates after modifying code:
  ```bash
  cd /var/www/signal-desk
  git pull origin main
  systemctl restart signaldesk
  ```
- [ ] **Uptime Monitoring**: Add a free monitor on [UptimeRobot.com](https://uptimerobot.com) pointing to `https://yourdomain.com/api/config` to alert you if the server ever goes down.

---

## Testing Your Live Deployment

Once deployed, verify that:
1. `GET https://yourdomain.com/api/config` returns `200 OK` with all 31+ assets.
2. Real-time streaming updates live without page refreshes.
3. Audio chimes play on BUY/SELL triggers.
4. Backtester generates 1,000 candles with 85% broker payout simulation.
5. Pocket Option Candle & Indicator Setup guide is responsive on mobile screens.
