# Operator Screening Criteria -- AI Qualification Guide

> Source: docs/KNOWLEDGE_BASE.md sections 4-8, 11

---

## Overview

This document defines the screening criteria for Live Stream Operator candidates. It covers the 11-step qualification flow, hard requirements (disqualifiers), hardware specifications, follow-up protocol, and safe formulations for job postings.

---

## 11-Step Qualification Questions (in order)

| Step | Question | Notes |
|------|----------|-------|
| 1 | **Full name** -- "What is your full name?" | Record for CRM |
| 2 | **PC ownership** -- "Do you have a personal PC or laptop?" | Options: PC / Laptop / No. No = disqualifier |
| 3 | **Age** -- "How old are you?" | Under 18 or over 30 = disqualifier |
| 4 | **Study/work status** -- "Are you currently studying or working?" | Options: Working / Student-distance / Student-in-person / Neither. In-person student = disqualifier |
| 5 | **English level** -- "What is your English level?" | Options: Beginner / B1 / B2 / C1+ / Native. Below B1 = disqualifier |
| 6 | **PC confidence** -- "Do you consider yourself a confident PC user?" | Record answer |
| 7 | **CPU model** -- "What is your processor model?" | Hint: dxdiag or Settings > System > About. Cross-reference with compatible CPU list |
| 8 | **GPU model** -- "What is your graphics card?" | Hint: dxdiag. Cross-reference with compatible GPU list |
| 9 | **Internet speed** -- "What is your internet speed?" | Hint: speedtest.net. Below 100 Mbps = disqualifier (unless upgrade within 1 week) |
| 10 | **Start date** -- "When would you be ready to start?" | More than 1 week delay = not preferred |
| 11 | **Contact** -- "Please share your Telegram @username or WhatsApp number" | Telegram format: @username. WhatsApp format: +1 234 567-8900 |

---

## Hard Requirements (Disqualifiers)

If a candidate fails any of these, they are **not eligible** for the operator position.

| Requirement | Threshold | Action on Failure |
|-------------|-----------|-------------------|
| PC/laptop | Must have one (Windows) | Reject. Keep on file if planning to buy soon |
| Age | 18-30 | Reject |
| Education | In-person students not eligible | Reject. Distance learning is OK |
| CPU | 4 cores / 8 threads minimum (Intel i3 10th gen+ / Ryzen 3 3000+) | Reject |
| GPU | Discrete graphics card required (GTX 1060 6GB+ / AMD RX 2019+) | Reject |
| MacBook | Not supported (macOS incompatible) | Reject |
| Internet | 100 Mbps minimum | Reject (or allow 1 week to upgrade) |
| LAN port | Ethernet / RJ-45 preferred | Warning only (not hard reject) |
| English | B1 (Intermediate) minimum | Reject |
| Start availability | Within 1 week preferred | Preference, not hard reject |
| Gender | Men only (partner platform rule) | Reject women candidates for operator role |

---

## Hardware Requirements Summary

### CPU -- Minimum Compatible

**Intel:** Core i3 10th gen or newer (i3-10100 and up)

| Gen | i3 | i5 | i7 | i9 |
|-----|----|----|----|----|
| 10th | i3-10100 | i5-10400 | i7-10700 | i9-10900 |
| 11th | i3-11100 | i5-11400 | i7-11700 | i9-11900 |
| 12th | i3-12100 | i5-12400 | i7-12700 | i9-12900 |
| 13th | i3-13100 | i5-13400 | i7-13700 | i9-13900 |
| 14th | i3-14100 | i5-14400 | i7-14700 | i9-14900 |

**AMD:** Ryzen 3 3000 series or newer

| Series | Ryzen 3 | Ryzen 5 | Ryzen 7 | Ryzen 9 |
|--------|---------|---------|---------|---------|
| 3000 | 3100 | 3600 | 3700X | 3900X |
| 5000 | 5300G | 5600X | 5800X | 5900X |
| 7000 | 7300X | 7600X | 7700X | 7900X |

**NOT supported:** Pentium, Celeron, Xeon, Atom, AMD FX, AMD A-series, Apple Silicon

### GPU -- Minimum Compatible

Discrete GPU required. Integrated graphics = not eligible.

**NVIDIA (compatible):**
- GTX 1060 6GB and above (10-series)
- GTX 1650 and above (16-series)
- RTX 2060 and above (20-series)
- RTX 3050 and above (30-series)
- RTX 4050 and above (40-series)
- RTX 5050 and above (50-series)

**AMD (compatible):** Any discrete RX from 2019 onwards (RX 5000+, RX 6000+, RX 7000+)

**NOT supported:** GT 710/730/1030, GTX 1060 3GB, RX 400/500 series, Radeon R/HD series, all integrated graphics

### Internet

- **Minimum:** 100 Mbps download (speedtest.net)
- **Preferred:** Wired (Ethernet/LAN) connection
- **Wi-Fi:** Acceptable only if 100+ Mbps with low latency
- **LAN port:** Must have Ethernet (RJ-45) port

### OS

- **Supported:** Windows 10, Windows 11
- **NOT supported:** macOS (any version)

---

## Follow-Up Protocol

| # | Scenario | Wait Time | Action |
|---|----------|-----------|--------|
| 1 | No answer after pitch | 2-4 hours | Soft reminder + "slots available" |
| 2 | No answer on follow-up | Next day | Brief reminder + "reply Yes" |
| 3 | "I'll think about it" | 12 hours | "Reserved a slot, want to keep it?" |
| 4 | No-show to interview | 1 hour | "Everything OK? Want to reschedule?" |
| 5 | Went silent during questions | 4 hours | "Stuck? Happy to help!" |

---

## Safe Formulations

### BANNED words (will get flagged/banned on platforms)

- webcam
- adult
- OnlyFans
- nsfw
- 18+
- sexy
- intimate
- HuntMe (internal name only)

### SAFE job titles

- Live Stream Operator
- Streaming Platform Operator
- Content Moderator
- Remote Technical Support for Streamers
- Behind-the-scenes streaming role

### SAFE job descriptions

- "Setting up streaming equipment and managing live chats"
- "Technical and organizational support for content creators"
- "Working behind the scenes on streaming platforms"
- "Equipment setup, chat moderation, and stream quality optimization"

### Branding rules

- **NEVER** mention "HuntMe" to candidates -- internal name only
- Present as: talent agency / talent management agency for streamers
- Position title for candidates: **Live Stream Operator** (not Moderator)
- If asked about the company: "We are a talent agency that discovers, trains, and promotes streaming talent on international platforms"
