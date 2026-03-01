# Immich Setup Guide
**Owner: Darrian Belcher | Created: 2026-02-25**

Self-hosted Google Photos replacement with built-in AI search, face recognition,
and CLIP semantic search — all running on your Beelink, zero cloud dependency.

---

## What You'll Have When Done

| Feature | How it works |
|---------|-------------|
| Auto photo backup from iPhone | Immich iPhone app → your homelab |
| Semantic search | Type "Jordan 1" or "receipt" → finds matching photos |
| Face recognition | Auto-groups every photo by person |
| Smart albums | Auto-organized by location, date, people |
| Duplicate detection | Flags duplicate photos automatically |
| Access from anywhere | Tailscale → `http://100.95.125.112:2283` |

---

## Prerequisites

- ✅ CT100 running at `100.95.125.112` (Tailscale) / `100.117.1.171` (local)
- ✅ Docker installed on CT100
- ✅ Tailscale on your Mac and iPhone
- ⏳ TrueNAS (optional — you can start on local disk and migrate later)

---

## Step 1 — SSH into CT100

From your Mac terminal:
```bash
ssh root@100.95.125.112
```

---

## Step 2 — Create the Immich directory and copy files

```bash
mkdir -p /opt/immich
mkdir -p /opt/immich/photos
cd /opt/immich
```

Now copy the files from this repo to CT100. From your **Mac terminal** (not SSH):
```bash
scp /Users/darrianbelcher/Downloads/darrian-budget/immich/docker-compose.yml root@100.95.125.112:/opt/immich/
scp /Users/darrianbelcher/Downloads/darrian-budget/immich/.env root@100.95.125.112:/opt/immich/
```

---

## Step 3 — Edit the .env file on CT100

Back in your SSH session:
```bash
nano /opt/immich/.env
```

Change the password to something you'll remember:
```
DB_PASSWORD=your_actual_password_here
```

Save: `Ctrl+O` → Enter → `Ctrl+X`

> ⚠️ If you have TrueNAS set up already, change UPLOAD_LOCATION too:
> ```
> UPLOAD_LOCATION=/mnt/truenas/photos
> ```
> If TrueNAS isn't set up yet, leave it as `/opt/immich/photos` — you can migrate later.

---

## Step 4 — Start Immich

```bash
cd /opt/immich
docker compose up -d
```

This pulls 4 images (~2GB total). First run takes 2-5 minutes depending on your connection.

Watch the startup:
```bash
docker compose logs -f
```

You'll see Postgres initialize, then Redis, then the Immich server start.
Press `Ctrl+C` to stop watching logs (containers keep running).

---

## Step 5 — Verify it's running

```bash
docker compose ps
```

All 4 containers should show `healthy` or `running`:
```
NAME                     STATUS
immich-server            Up (healthy)
immich-machine-learning  Up
immich-redis             Up (healthy)
immich-postgres          Up (healthy)
```

Test the health endpoint:
```bash
curl http://localhost:2283/api/server/ping
# Should return: {"res":"pong"}
```

---

## Step 6 — Create your admin account

Open in your browser:
```
http://100.95.125.112:2283
```

1. Click **"Getting Started"**
2. Create your admin account:
   - Email: your email
   - Name: Darrian
   - Password: something strong
3. Click **"Create Account"**

> This is the only account — it's your personal instance, not shared.

---

## Step 7 — Install the iPhone app and set up auto-backup

1. **App Store** → search **"Immich"** → Install (it's free)
2. Open the app
3. **Server URL:** `http://100.95.125.112:2283`
   > ⚠️ Tailscale must be ON on your iPhone for this to work
4. Log in with the account you just created
5. Go to **Profile → Backup** → toggle **"Background Backup" ON**
6. Tap **"Start Backup"** — it will begin uploading your entire camera roll

> 💡 **Tip:** Do the initial backup on WiFi at home (faster). After that, new photos
> back up automatically whenever Tailscale is on.

---

## Step 8 — Trigger AI indexing

After your photos upload, kick off the AI jobs:

1. In the Immich web UI → **Administration** (top right menu)
2. Click **"Jobs"**
3. Run these jobs (click the play button on each):
   - **"Smart Search"** — runs CLIP on every photo (enables semantic search)
   - **"Face Detection"** — detects and groups faces
   - **"Duplicate Detection"** — finds duplicate photos

These run in the background. On a Ryzen 7, expect:
- ~1-3 seconds per photo for CLIP indexing
- 1,000 photos ≈ 15-45 minutes
- 10,000 photos ≈ 2-8 hours (let it run overnight)

---

## Step 9 — Try the AI search

Once Smart Search finishes on even a few hundred photos, try it:

In the search bar, type:
- `sneaker` → finds every shoe photo
- `receipt` → finds every receipt (great for HSA reimbursements)
- `Jordan 1` → finds Jordan 1s even if the filename is IMG_4821.jpg
- `white shoes red laces` → CLIP finds photos matching the visual concept
- `outdoor` → finds outdoor photos
- `food` → finds food photos

This is **not** keyword search — it's semantic. It understands what's in the image.

---

## Step 10 — Name your faces

After Face Detection runs:
1. Go to **Explore → People**
2. You'll see face clusters — click each one
3. Type the person's name
4. Immich applies that name to every photo of that person going forward

---

## Migrating to TrueNAS (When Drives Are Set Up)

When TrueNAS is running and your `tank/photos` dataset is mounted:

```bash
# 1. Stop Immich
cd /opt/immich
docker compose down

# 2. Move existing photos to TrueNAS
mv /opt/immich/photos/* /mnt/truenas/photos/

# 3. Update .env
nano /opt/immich/.env
# Change: UPLOAD_LOCATION=/mnt/truenas/photos

# 4. Restart
docker compose up -d
```

Immich picks up the new location automatically — no re-indexing needed.

---

## Useful Commands

```bash
# Check status
cd /opt/immich && docker compose ps

# View logs
docker compose logs -f immich-server

# Stop everything
docker compose down

# Update to latest version
docker compose pull && docker compose up -d

# Check how much disk photos are using
du -sh /opt/immich/photos
```

---

## Ports Used

| Port | Service |
|------|---------|
| 2283 | Immich web UI + API |

No conflicts with your existing services (budget app: 8501, AURA: 8000, Portainer: 9000, NPM: 81).

---

## Quick Reference

| I want to... | Do this |
|-------------|---------|
| Open Immich on Mac | `http://100.95.125.112:2283` (Tailscale on) |
| Open Immich on iPhone | Immich app (Tailscale on) |
| Search photos by concept | Search bar → type anything |
| See all photos of a person | Explore → People → tap their face |
| Check AI job progress | Administration → Jobs |
| Add more storage | Update UPLOAD_LOCATION in .env → restart |
| Update Immich | `docker compose pull && docker compose up -d` |
