# Deployment Guide: Professional VPS Setup

Running Baymax on a VPS in **Mumbai (ap-south-1)** reduces latency from ~200ms down to **<10ms**, significantly reducing slippage.

## 🏢 Recommended Server Specs
- **Provider**: AWS (Mumbai) or DigitalOcean (Bangalore).
- **OS**: Ubuntu 22.04 LTS.
- **Specs**: 1 vCPU, 2GB RAM (Minimum).

## 🐋 1. Containerized Deployment (Recommended)

### Create the Dockerfile
In the project root, create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run with unbuffered output for real-time logs
ENTRYPOINT ["python", "-u", "-m", "trading_system.main"]
```

### Build and Run
```bash
# Build the image
docker build -t baymax-algo .

# Run as a background daemon
docker run -d \
  --name trading-bot \
  --restart always \
  --env-file .env \
  baymax-algo --config config_multi.json --source dhan_v2 --execution dhan
```

## 🛠 2. Direct Deployment (Ubuntu + PM2)

If you don't want to use Docker, use **PM2** to keep the bot running 24/7.

```bash
# 1. Install Dependencies
sudo apt update && sudo apt install -y python3-pip

# 2. Install PM2
sudo npm install -g pm2

# 3. Launch Bot
pm2 start "python3 -u -m trading_system.main --config config_multi.json --source dhan_v2 --execution dhan" --name BaymaxBot

# 4. Save for Auto-Reboot
pm2 save
pm2 startup
```

## 📊 Viewing Logs on VPS
To see what the bot is doing in real-time from your terminal:
```bash
# Docker
docker logs -f trading-bot

# PM2
pm2 logs BaymaxBot
```

## 🛰️ Networking Impact
| Location | Latency to NSE | Status |
| :--- | :--- | :--- |
| Home PC | ~221 ms | ⚠️ High Slippage |
| **AWS Mumbai** | **~2.8 ms** | **⭐ Institutional** |
| DigitalOcean BLR | ~12.2 ms | ✅ Excellent |
