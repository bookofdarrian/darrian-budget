# iCloud Storage — How to Expand & Manage It
**For: Darrian Belcher | Updated: 2025-02-25**

---

## Current iCloud Plans & Pricing (2025)

Apple offers iCloud+ plans through **iCloud+** (includes privacy features):

| Plan | Storage | Price/Month |
|------|---------|-------------|
| Free | 5 GB | $0 |
| iCloud+ 50 GB | 50 GB | $0.99 |
| iCloud+ 200 GB | 200 GB | $2.99 |
| iCloud+ 2 TB | 2 TB | $9.99 |
| iCloud+ 6 TB | 6 TB | $29.99 |
| iCloud+ 12 TB | 12 TB | $59.99 |

> **All paid plans include:** iCloud Private Relay, Hide My Email, Custom Email Domain, HomeKit Secure Video

---

## How to Upgrade iCloud Storage

### On Your iPhone / iPad
1. Open **Settings**
2. Tap your **name** (Apple ID) at the top
3. Tap **iCloud**
4. Tap **Manage Account Storage** (or **Manage Storage**)
5. Tap **Change Storage Plan** (or **Upgrade to iCloud+**)
6. Select your plan → **Buy** → confirm with Face ID / Touch ID

### On Your Mac
1. Click **Apple menu ()** → **System Settings**
2. Click your **name** (Apple ID) at the top left
3. Click **iCloud**
4. Click **Manage** (bottom right)
5. Click **Change Storage Plan**
6. Select your plan → **Next** → enter Apple ID password

### On the Web (iCloud.com)
1. Go to https://www.icloud.com
2. Sign in with your Apple ID
3. Click your **name** (top right) → **Account Settings**
4. Under **Storage**, click **Change Storage Plan**
5. Select your plan and confirm

---

## Family Sharing — Share Storage With Family

If you have **Family Sharing** set up, you can share your iCloud+ storage with up to 5 family members.

### How to Set Up Family Sharing for iCloud Storage
1. On your iPhone: **Settings → [Your Name] → Family Sharing**
2. Tap **Set Up Your Family** (or add members if already set up)
3. Once family is set up, your iCloud+ storage is automatically shared
4. Each person uses from the same pool — you can see who's using what

> **Note:** Only the family organizer pays. Everyone shares the same storage pool.
> If you're on 200 GB and have 3 family members, all 3 share that 200 GB.

---

## What's Eating Your iCloud Storage?

### Check What's Using Space (iPhone)
1. **Settings → [Your Name] → iCloud → Manage Account Storage**
2. You'll see a breakdown by app:
   - Photos (usually the biggest)
   - iCloud Drive
   - iCloud Backup
   - Messages
   - Mail

### Check on Mac
1. **Apple menu → System Settings → [Your Name] → iCloud → Manage**
2. Same breakdown — click any app to see details

---

## How to Free Up iCloud Space (Before Upgrading)

### 1. Optimize iPhone Photos
Instead of storing full-res photos in iCloud AND on your phone:
- **Settings → [Your Name] → iCloud → Photos**
- Turn on **Optimize iPhone Storage**
- This keeps small previews on your phone, full-res in iCloud only

### 2. Delete Old iCloud Backups
Old backups from previous iPhones take up tons of space:
- **Settings → [Your Name] → iCloud → Manage Account Storage → Backups**
- Delete backups from old devices you no longer use

### 3. Clean Up iCloud Drive
- On Mac: Open **Finder → iCloud Drive**
- Delete files you don't need
- Empty the Trash after

### 4. Turn Off iCloud for Apps You Don't Need
- **Settings → [Your Name] → iCloud**
- Toggle off apps that don't need cloud sync (games, apps you don't use)

### 5. Delete Old Messages Attachments
Messages with photos/videos take up a lot of space:
- **Settings → [Your Name] → iCloud → Manage Account Storage → Messages**
- Review and delete large conversations

---

## iCloud vs. Home Lab Storage — Which to Use for What

Since you're building a home lab with 2x 4TB drives (8TB raw, 4TB usable in RAID 1),
here's how to think about what goes where:

| Data Type | Best Storage | Why |
|-----------|-------------|-----|
| iPhone photos/videos | iCloud Photos | Automatic, syncs to all devices |
| Mac documents | iCloud Drive | Accessible everywhere |
| Budget app data | Home lab (PostgreSQL) | You control it, no monthly fee |
| App backups | Home lab (TrueNAS) | 4TB free vs. paying Apple |
| Large media files | Home lab NAS | Too big for iCloud, cheaper |
| iPhone backup | iCloud (keep 1 backup) | Convenient for restore |
| Code / repos | GitHub + home lab | Already doing this |

### The Smart Move: Hybrid Approach
- Keep iCloud at **200 GB** ($2.99/mo) for photos + iPhone backup
- Use your **home lab NAS** for everything else (large files, backups, media)
- This saves you from paying Apple $9.99/mo for 2TB when your home lab has 4TB free

---

## Set Up iCloud Drive on Your Mac (If Not Already)

```
Apple menu → System Settings → [Your Name] → iCloud
→ Turn on iCloud Drive
→ Click "Options" next to iCloud Drive
→ Check: Desktop & Documents Folders (syncs your Desktop to iCloud)
```

Now your Desktop and Documents are automatically backed up to iCloud.

---

## iCloud Private Relay (Included with iCloud+)

All paid iCloud+ plans include **Private Relay** — Apple's privacy feature that hides your IP and browsing from your ISP.

To enable:
- **Settings → [Your Name] → iCloud → Private Relay → Turn On**
- Or on Mac: **System Settings → [Your Name] → iCloud → Private Relay**

> **Note:** Private Relay may slow down some connections slightly. If you notice issues, you can turn it off per-network under Wi-Fi settings.

---

## iCloud Keychain — Store Passwords

iCloud Keychain syncs your passwords across all Apple devices for free (doesn't use your storage quota).

To enable:
- **Settings → [Your Name] → iCloud → Passwords and Keychain → Turn On**

---

## Troubleshooting iCloud Storage Issues

### "iCloud storage is full" notification
1. Check what's using space (see above)
2. Delete old backups from old devices
3. Upgrade your plan if needed

### Photos not syncing
1. Check you're on WiFi (iCloud Photos prefers WiFi)
2. **Settings → Photos → iCloud Photos** — make sure it's on
3. Check your iCloud storage isn't full

### iCloud Drive not syncing on Mac
```bash
# Force iCloud to re-sync on Mac:
killall bird
# "bird" is the iCloud sync daemon — it restarts automatically
```

### Can't upgrade storage (payment issue)
1. **Settings → [Your Name] → Payment & Shipping**
2. Update your payment method
3. Try upgrading again

---

## Quick Summary — What to Do Right Now

1. **Check your current usage:**
   iPhone → Settings → [Your Name] → iCloud → Manage Account Storage

2. **If you're near the 5GB free limit:**
   - Delete old device backups first (biggest space saver)
   - Then upgrade to **200 GB for $2.99/mo** — best value for most people

3. **If you have a family:**
   - Set up Family Sharing so everyone shares your plan

4. **Long term:**
   - Use your home lab NAS for large files
   - Keep iCloud for photos + iPhone backup only
   - 200 GB plan is usually enough with this hybrid approach

---

## Apple One — Bundle Deal (If You Use Apple Services)

If you subscribe to Apple Music, Apple TV+, or Apple Arcade, **Apple One** bundles them with iCloud storage:

| Plan | Includes | Price/Month |
|------|---------|-------------|
| Individual | Apple Music + TV+ + Arcade + 50GB iCloud | $19.95 |
| Family | Same + Family Sharing for 6 people + 200GB iCloud | $25.95 |
| Premier | All above + News+ + Fitness+ + 2TB iCloud | $37.95 |

If you already pay for 2+ Apple services separately, Apple One saves money.
