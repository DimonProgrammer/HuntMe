# Landing Page — Backend Setup Guide

## Overview

The application form submits data to a **Google Apps Script** web app (free, unlimited).
Data lands in a Google Sheet. Optionally triggers a Telegram notification on every new lead.

---

## Step 1 — Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → create a new spreadsheet
2. Name it **"Apex Talent Leads"**
3. Rename the first sheet tab to **"Leads"**
4. Add these headers in row 1 (exactly as shown):

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| Timestamp | Name | WhatsApp | Country | CPU | GPU | Age | English | Status |

---

## Step 2 — Create the Apps Script

1. In the Google Sheet: **Extensions → Apps Script**
2. Delete all existing code in the editor
3. Paste this code:

```javascript
function doPost(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Leads') || ss.getActiveSheet();
  const data = JSON.parse(e.postData.contents);

  sheet.appendRow([
    new Date(),
    data.name,
    data.whatsapp,
    data.country,
    data.cpu,
    data.gpu,
    data.age,
    data.english,
    data.status
  ]);

  // ── OPTIONAL: Telegram notification ──────────────────────────────────────
  // 1. Get your bot token from @BotFather on Telegram
  // 2. Get your chat ID: message @userinfobot
  // 3. Uncomment the 3 lines below and fill in your values

  // const TOKEN   = 'YOUR_BOT_TOKEN_HERE';
  // const CHAT_ID = 'YOUR_CHAT_ID_HERE';
  // const flag    = data.country === 'PH' ? '🇵🇭' : data.country === 'NG' ? '🇳🇬' : '🌍';
  // UrlFetchApp.fetch(
  //   `https://api.telegram.org/bot${TOKEN}/sendMessage?` +
  //   `chat_id=${CHAT_ID}&` +
  //   `text=${encodeURIComponent(`${flag} New lead: ${data.name}\nWA: ${data.whatsapp}\nCountry: ${data.country}\nCPU: ${data.cpu} | GPU: ${data.gpu}`)}`
  // );
  // ─────────────────────────────────────────────────────────────────────────

  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok' }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

4. Click **Save** (Ctrl+S), name the project "Apex Talent Form"

---

## Step 3 — Deploy as Web App

1. Click **Deploy → New deployment**
2. Click the gear icon next to "Type" → select **Web app**
3. Set:
   - Description: `Apex Talent lead capture v1`
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Click **Deploy**
5. Authorize the script when prompted (Google account pop-up)
6. **Copy the Web App URL** — it looks like:
   `https://script.google.com/macros/s/AKfycb.../exec`

---

## Step 4 — Connect to the Landing Page

Open `landing/index.html` and find this line (near the bottom, in the `<script>` block):

```javascript
const GOOGLE_SCRIPT_URL = 'PASTE_YOUR_APPS_SCRIPT_URL_HERE';
```

Replace `'PASTE_YOUR_APPS_SCRIPT_URL_HERE'` with your copied URL:

```javascript
const GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycb.../exec';
```

Save the file.

---

## Step 5 — Test

1. Open `landing/index.html` locally in a browser
2. Fill out the form and submit
3. Go to your Google Sheet → check that a new row appeared
4. If Telegram configured: check you received the notification

---

## Step 6 — Deploy to Vercel

```bash
# Install Vercel CLI (one-time)
npm i -g vercel

# From project root (d:/Projects/HuntMe)
vercel --prod
```

Or: push to GitHub → Vercel auto-deploys (if project connected in Vercel dashboard).

The `vercel.json` is already configured:
- Output directory: `landing/`
- Clean URLs: enabled (no `.html` in URL)

---

## Troubleshooting

**Form submits but no row in Sheet:**
- Make sure the sheet tab is named exactly `Leads`
- Re-deploy the script after any code changes (Deploy → Manage deployments → New version)

**CORS error in browser console:**
- This is expected for `fetch` to Apps Script — the request still goes through
- The `try/catch` in the form handler suppresses this and still shows success

**Want to re-deploy after script changes:**
- Always create a **new deployment version** (not edit existing) — otherwise the old cached version runs
