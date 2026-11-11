# Complete Guide: Running SignalDesk with $0 (No Paid VPS Required)

> **Core Truth:** You do **not** need a paid VPS or a 24/7 cloud server to make money with SignalDesk. Professional prop traders and day traders almost never trade 24 hours a day. The market offers high-probability setups during specific session windows (London & New York). Running the bot locally on your current computer during these hours costs **$0.00** and actually gives you faster execution speed than cheap budget VPS servers.

---

## Table of Contents
1. [Why You Don't Actually Need a 24/7 VPS](#1-why-you-dont-actually-need-a-247-vps)
2. [Method 1: Run Locally on Your PC (Best & 100% Free)](#method-1-run-locally-on-your-pc-best--100-free)
3. [Method 2: Oracle Cloud Always Free Tier (Permanent Free Linux VPS)](#method-2-oracle-cloud-always-free-tier-permanent-free-linux-vps)
4. [Method 3: Free Cloud Container Hosting (Render / Koyeb / Fly.io)](#method-3-free-cloud-container-hosting-render--koyeb--flyio)
5. [Method 4: Free Trial Cloud Credits ($200–$300 for 2–3 Months)](#method-4-free-trial-cloud-credits-200300-for-23-months)
6. [Method 5: Repurpose an Old Spare Laptop or PC](#method-5-repurpose-an-old-spare-laptop-or-pc)
7. [Remote Control from Phone with ngrok / Cloudflare Tunnel](#7-remote-control-from-phone-with-ngrok--cloudflare-tunnel)
8. [Summary & Recommendation](#8-summary--recommendation)

---

## 1. Why You Don't Actually Need a 24/7 VPS

Many beginner traders think a trading bot must stay on 24 hours a day, 7 days a week. In reality:

1. **Volume & Volatility Windows:**
   - **London Session:** 08:00 – 16:00 UTC (High volume, clean trends).
   - **New York Session:** 13:00 – 21:00 UTC (Peak volume, strong directional momentum).
   - **Asian Off-Hours / Dead Midnight:** Low volume, unpredictable ranging wicks, high risk of false breakouts.
2. **Quality Over Quantity:**
   - A trader who takes **2–3 high-confluence trades a day** during active sessions will consistently beat someone taking 50 trades in dead Asian midnight chop.
3. **Zero Latency Advantage:**
   - When running on your local machine, the SignalDesk dashboard is directly accessible at `http://127.0.0.1:8000` with **0 ms latency** and direct connection to your Telegram phone app.

---

## Method 1: Run Locally on Your PC (Best & 100% Free)

This is the recommended setup when starting with zero capital.

### How to Run During Your Trading Hours
1. Turn on your PC / laptop when you sit down for your trading session.
2. Open PowerShell or Command Prompt in the project folder:
   ```powershell
   cd c:\Users\XPRISTO\Desktop\signal-desk-2
   python run.py
   ```
3. Open your browser to `http://localhost:8000`.
4. Your Telegram bot will alert your phone the second a confluence signal forms.
5. Execute the trade manually on Pocket Option or your broker.
6. When your trading session ends (e.g., after 2–4 hours), press `Ctrl + C` in PowerShell to stop the bot and shut down your computer.

### How to Prevent Your Windows PC from Sleeping While Trading
If you want to step away from your desk for a coffee or lunch while keeping the bot running:
1. Open **Windows Settings** -> **System** -> **Power & battery**.
2. Click **Screen and sleep**.
3. Set **"When plugged in, put my device to sleep after"** to **Never** (or `2 hours` / `4 hours`).
4. Set the screen to turn off after 5 minutes to save monitor power while the CPU keeps running the Python WebSocket.

---

## Method 2: Oracle Cloud Always Free Tier (Permanent Free Linux VPS)

Oracle Cloud Infrastructure (OCI) offers an **Always Free** tier that never expires and does not charge your card.

### What Oracle Gives You for $0:
- **Ampere A1 ARM Compute:** Up to 4 OCPUs and 24 GB of RAM (can be split into 1 or 2 virtual machines) — completely free forever!
- Or **2 AMD Micro VMs:** 1/8 OCPU, 1 GB RAM each — completely free forever!
- **200 GB Block Storage** (free forever).

### How to Set It Up:
1. Go to [https://www.oracle.com/cloud/free/](https://www.oracle.com/cloud/free/) and sign up.
   *(Note: You will need a credit or debit card with $1 for temporary anti-fraud verification; it is refunded immediately).*
2. Choose your nearest home region (e.g., Frankfurt, London, or Ashburn).
3. In the OCI Console:
   - Click **Create a VM Instance**.
   - Choose **Ubuntu 22.04 LTS** or **Ubuntu 24.04**.
   - Select **Ampere (ARM)** with 2 OCPUs and 12 GB RAM (or 1 OCPU and 6 GB RAM).
   - Download the generated SSH Private Key (`.key` file).
4. Connect from your Windows PowerShell via SSH:
   ```bash
   ssh -i your-key.key ubuntu@<YOUR_INSTANCE_PUBLIC_IP>
   ```
5. Install Python and clone your SignalDesk repo:
   ```bash
   sudo apt update && sudo apt install -y python3-pip git tmux
   git clone https://github.com/yourusername/signal-desk-2.git
   cd signal-desk-2
   pip install -r requirements.txt
   ```
6. Run it 24/7 inside a background `tmux` or `systemd` session:
   ```bash
   tmux new -s bot
   python3 run.py
   ```
   *(Press `Ctrl+B`, then `D` to detach. The bot runs continuously in the cloud for $0).*

---

## Method 3: Free Cloud Container Hosting (Render / Koyeb / Fly.io)

If you do not want to set up an Oracle Linux VM, several modern cloud platforms provide free container compute:

### A. Render.com
- **Free Tier:** 750 free instance hours per month on web services.
- **Math:** 750 hours $\div$ 24 hours/day = **31.25 days** (covers an entire month for free!).
- **How to deploy:**
  1. Create a free account at [render.com](https://render.com).
  2. Click **New +** -> **Web Service**.
  3. Connect your GitHub repository `signal-desk-2`.
  4. Environment: **Python 3**.
  5. Build Command: `pip install -r requirements.txt`.
  6. Start Command: `python run.py`.
  7. Add Environment Variables:
     - `TELEGRAM_BOT_TOKEN`: your bot token.
     - `TELEGRAM_CHAT_ID`: your chat ID.
  8. Click **Deploy**. Render gives you a free HTTPS URL (e.g., `https://signal-desk-bot.onrender.com`).

### B. Koyeb
- Offers a permanent free "Eco" nano micro-instance with 512MB RAM and 2.5GB storage.
- Connects directly to GitHub and auto-deploys when you push code.

---

## Method 4: Free Trial Cloud Credits ($200–$300 for 2–3 Months)

All major enterprise cloud providers offer large welcome bonuses with no upfront cost:

| Cloud Provider | Free Bonus | Trial Period | Card Required? |
| :--- | :--- | :--- | :--- |
| **Google Cloud (GCP)** | **$300 USD** free credit | 90 days | Yes (verified with $0 charge) |
| **DigitalOcean** | **$200 USD** free credit | 60 days | Yes |
| **Microsoft Azure** | **$200 USD** free credit | 30 days + 12 mo free services | Yes |
| **Vultr** | **$100–$250 USD** credit promos | 30 days | Yes |
| **Linode / Akamai** | **$100 USD** free credit | 60 days | Yes |

### Rotation Strategy:
1. Start with Google Cloud's **$300 for 90 days** -> launch an e2-micro instance -> Run 3 months free.
2. Switch to DigitalOcean's **$200 for 60 days** -> launch a basic $4 droplet -> Run 2 months free.
3. Switch to Azure or Linode -> Run another 2 months free.
4. By the time the free trials expire, your trading account profits will easily cover a $4/month server.

---

## Method 5: Repurpose an Old Spare Laptop or PC

If you or a friend/family member have an old laptop or desktop sitting in a closet:

1. Even an old 10-year-old laptop with 2GB of RAM is more than fast enough for Python and WebSocket streams.
2. **Advantages of an old laptop:**
   - **Built-in Battery Backup (UPS):** If the power flickers, the battery keeps your bot alive!
   - **Low Power Consumption:** An idle laptop uses only 10–15 Watts of electricity (less than $1/month in power).
   - **Zero Cost:** Completely free hardware you already own.
3. Simply install Windows or Ubuntu Desktop, plug it in near your Wi-Fi router, install Python, and run `python run.py`.

---

## 7. Remote Control from Phone with ngrok / Cloudflare Tunnel

If you run the bot on your home PC or laptop, how can you view the web dashboard while away from home on your phone?

Use a **100% free Cloudflare Tunnel** or **ngrok**:

### Option A: Cloudflare Tunnel (100% Free, No Port Forwarding)
1. Download `cloudflared` for Windows (free from Cloudflare).
2. Run in a terminal:
   ```cmd
   cloudflared tunnel --url http://localhost:8000
   ```
3. Cloudflare gives you a secure random HTTPS link (e.g. `https://random-words.trycloudflare.com`).
4. Bookmark this link on your iPhone or Android browser. You can now view your live SignalDesk dashboard from anywhere in the world while your home PC runs it!

### Option B: ngrok (Free Tier)
1. Download ngrok from [ngrok.com](https://ngrok.com).
2. Run:
   ```cmd
   ngrok http 8000
   ```
3. Open the generated HTTPS URL on your phone.

---

## 8. Summary & Recommendation

| Approach | Cost | Difficulty | Best For |
| :--- | :--- | :--- | :--- |
| **1. Local PC during trading sessions** | **$0.00** | Easiest (1 click) | **Recommended for starting today** |
| **2. Oracle Cloud Always Free** | **$0.00** | Medium (Linux / SSH) | Best if you want a true 24/7 cloud server |
| **3. Render.com / Koyeb** | **$0.00** | Easy (GitHub deploy) | Best if you don't want to manage Linux OS |
| **4. Cloud Free Trials (GCP $300)** | **$0.00** | Easy | Best for 3–6 months of premium cloud servers |
| **5. Old Spare Laptop** | **$0.00** | Easy | Best home server with built-in battery backup |

### What You Should Do Right Now:
Do not let the lack of a VPS hold you back. Open PowerShell, run `python run.py`, trade your 2–3 hour session with real disciplined confluence signals, and let your trading profits fund your infrastructure upgrades later.

