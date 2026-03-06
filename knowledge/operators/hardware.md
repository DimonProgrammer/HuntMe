# Hardware Compatibility Guide -- Streaming Operator

> Source: Training Examples EN/START_HERE_Documentation/Operators/07_Hardware_Compatibility_Guide.html

*Internal Guide for Recruitment Team*

---

## Document Structure

1. Overview & How to Use This Guide
2. Quick Compatibility Check
3. Intel Core Processors (10th-14th Gen)
4. AMD Ryzen Processors
5. Incompatible Processors
6. NVIDIA GeForce GPUs
7. AMD Radeon GPUs
8. Internet Requirements
9. Additional Hardware Requirements

---

## Section 1: Overview & How to Use This Guide

### Purpose

This document is a standalone reference for verifying whether an operator candidate's hardware meets the minimum requirements for the **Streaming Platform Operator** position.

Use it during calls or messenger conversations when a candidate provides their hardware specifications.

### How to Verify Hardware

- Ask the candidate for their **processor (CPU) model** -- look it up in the Intel or AMD CPU tables
- Ask for their **graphics card (GPU) model** -- look it up in the NVIDIA or AMD GPU sections
- If the candidate doesn't know their specs, ask them to check: **Settings > System > About** (Windows) or run **dxdiag**
- Verify Internet speed and Additional requirements

---

## Section 2: Quick Compatibility Check

> **Speed Check:** Use this section for a fast yes/no decision before looking up exact models in the full tables.

### Minimum Requirements Summary

- **CPU:** Intel Core i3 10th gen or newer / AMD Ryzen 3 3000-series or newer
- **GPU:** NVIDIA GTX 1060 6GB or newer / AMD Radeon from 2019 or newer
- **Internet:** 100 Mbps minimum (wired connection preferred)
- **LAN port:** Required (Ethernet / RJ-45)
- **OS:** Windows only (no macOS)

**Instant Pass:** If the candidate has **Intel Core i5/i7 12th gen+** or **Ryzen 5/7 5000-series+** with an **RTX 3060+** and **100+ Mbps wired internet** -- they are compatible. No need to look up individual models.

**INSTANT FAIL:** If the candidate uses a **MacBook**, **Intel Pentium/Celeron**, **Intel Xeon**, or **AMD FX** -- they are **not eligible**. No further hardware check needed.

---

## Section 3: Intel Core Processors (10th-14th Gen)

### Core i3 -- Entry Level

| 10th Gen | 11th Gen | 12th Gen | 13th Gen | 14th Gen |
|---|---|---|---|---|
| i3-10100, i3-10100F, i3-10105, i3-10105F, i3-10300 | i3-11100, i3-11100F | i3-12100, i3-12100F, i3-12300, i3-12300T | i3-13100, i3-13100F | i3-14100, i3-14100F |

### Core i5 -- Mid Range

| 10th Gen | 11th Gen | 12th Gen | 13th Gen | 14th Gen |
|---|---|---|---|---|
| i5-10400, i5-10600K, i5-10300H, i5-10400H, i5-10500H | i5-11400, i5-11600K | i5-12400, i5-12600K, i5-12500H, i5-12450H, i5-12600H | i5-13400, i5-13600K, i5-13500H | i5-14400, i5-14600K, i5-14500H |

### Core i7 -- High Performance

| 10th Gen | 11th Gen | 12th Gen | 13th Gen | 14th Gen |
|---|---|---|---|---|
| i7-10700K, i7-10850H | i7-11700K | i7-12700K, i7-12800H, i7-12650H | i7-13700K, i7-13800H, i7-13650H | i7-14700K, i7-14800H, i7-14650H |

### Core i9 -- Enthusiast

| 10th Gen | 11th Gen | 12th Gen | 13th Gen | 14th Gen |
|---|---|---|---|---|
| i9-10850K, i9-10900K | i9-11900K | i9-12900K, i9-12900H | i9-13900K, i9-13900H | i9-14900K, i9-14900H |

> **Note:** Laptop variants (H-suffix) and desktop variants (K-suffix, no suffix) are both compatible. The "F" suffix means no integrated graphics -- still compatible as long as the candidate has a dedicated GPU.

---

## Section 4: AMD Ryzen Processors

### Ryzen 3 -- Entry Level

| Compatible Ryzen 3 Models |
|---|
| Ryzen 3 3100, 3300X, 4100, 4300G, Pro 4350GE, 5300G, 5300U, 5400U, 5425U, 8300G |

### Ryzen 5 -- Mid Range

| Compatible Ryzen 5 Models |
|---|
| Ryzen 5 1500X, 1600, 1600X, 2400G, 2400GE, 2500U, 2500X, 2600, 2600H, 2600X, 3400G, 3500U, 3550H, 3600, 3600X, 5500, 5500GT, 5600, 5600G, 5600GE, 5600GT, 5600X, 5600X3D, 7500F, 7600, 7600X, 7600X3D, 8400F, 8500G, 8600G, 9600X, PRO 2400G, PRO 2400GE, PRO 2500U, PRO 7645 |

### Ryzen 7 -- High Performance

| Compatible Ryzen 7 Models |
|---|
| Ryzen 7 1700, 1700X, 1800X, 2700, 2700U, 2700X, 2800H, 3700U, 3700X, 3750H, 3800X, 3800XT, 4700U, 5700, 5700G, 5700X, 5700X3D, 5800X, 5800X3D, 5800XT, 7700, 7700X, 7800X3D, 8700F, 8700G, 9700X, PRO 2700U, PRO 7745 |

### Ryzen 9 -- Enthusiast

| Compatible Ryzen 9 Models |
|---|
| Ryzen 9 3900, 3900X, 3900XT, 3950X, 5900X, 5900XT, 5950X, 7900, 7900X, 7900X3D, 7950X, 7950X3D, 9900X, 9950X, PRO 7945 |

---

## Section 5: Incompatible Processors

**NOT ELIGIBLE:** If the candidate's processor falls into any of the categories below, they **cannot** work as an operator. Their hardware does not meet the minimum requirements.

| Processor Family | Details | Reason |
|---|---|---|
| **AMD FX** | All models (FX-4100, FX-6300, FX-8350, etc.) | Outdated architecture, insufficient single-thread performance |
| **Intel Xeon** | All models (server/workstation processors) | Server-grade, not optimized for streaming workloads |
| **Intel Pentium** | All models (Gold, Silver, etc.) | Insufficient processing power for simultaneous OBS + streaming |
| **Intel Celeron** | All models | Budget tier, cannot handle streaming software requirements |
| **MacBook processors** | Apple M1, M2, M3, Intel-based MacBooks | macOS is not compatible with required streaming software configuration |

> **How to Handle:** If a candidate has an incompatible processor, politely explain: *"Unfortunately, your current hardware configuration does not meet the minimum requirements for this position. We recommend upgrading your processor if you're interested in future opportunities."*

---

## Section 6: NVIDIA GeForce GPUs

| Series 10 (GTX) | Series 16 (GTX) | Series 20 (RTX) | Series 30 (RTX) | Series 40 (RTX) | Series 50 (RTX) |
|---|---|---|---|---|---|
| GTX 1060 6GB, GTX 1070, GTX 1070 Ti, GTX 1080, GTX 1080 Ti | GTX 1630, GTX 1650, GTX 1650 Super, GTX 1660, GTX 1660 Super, GTX 1660 Ti | RTX 2060, RTX 2060 Super, RTX 2070, RTX 2070 Super, RTX 2080, RTX 2080 Super, RTX 2080 Ti | RTX 3050, RTX 3060, RTX 3060 Ti, RTX 3070, RTX 3070 Ti, RTX 3080, RTX 3080 Ti, RTX 3090, RTX 3090 Ti | RTX 4050, RTX 4060, RTX 4060 Ti, RTX 4070, RTX 4070 Super, RTX 4070 Ti, RTX 4070 Ti Super, RTX 4080, RTX 4080 Super, RTX 4090 | RTX 5050, RTX 5060, RTX 5060 Ti, RTX 5070, RTX 5070 Ti, RTX 5080, RTX 5090 |

**Ti & Super Variants:** If a listed model has a **Ti** or **SUPER** variant, that variant is **also compatible**. Example: GTX 1650 (listed) -> GTX 1650 Ti, GTX 1650 SUPER -> both compatible.

**NOT COMPATIBLE:** **GTX 1060 3GB** is NOT compatible -- only the **6GB version** meets requirements. If the candidate mentions "GTX 1060", always confirm the VRAM amount.

---

## Section 7: AMD Radeon GPUs

### Compatibility Rule

**AMD GPUs released from 2019 onwards are accepted.** This includes:

- **RX 5000 series** (RDNA) -- RX 5500 XT, RX 5600 XT, RX 5700, RX 5700 XT
- **RX 6000 series** (RDNA 2) -- RX 6500 XT, RX 6600, RX 6600 XT, RX 6700 XT, RX 6800, RX 6800 XT, RX 6900 XT, RX 6950 XT
- **RX 7000 series** (RDNA 3) -- RX 7600, RX 7700 XT, RX 7800 XT, RX 7900 GRE, RX 7900 XT, RX 7900 XTX
- **RX 9000 series** (RDNA 4) -- all models

**NOT COMPATIBLE:** AMD GPUs **older than 2019** (RX 400 series, RX 500 series, Vega series, and older) are **not compatible**.

---

## Section 8: Internet Requirements

### Minimum Speed

**100 Mbps** download speed (measured via **speedtest.net**).

Ask the candidate to run a speed test during the call/conversation and share the result (number or screenshot).

### Connection Type

- **Wired (Ethernet/LAN)** -- strongly preferred for stability
- **Wi-Fi** -- acceptable only if speed test confirms 100+ Mbps with low latency
- The candidate's PC/laptop must have a **LAN (Ethernet) port**

> **If Speed Is Below 100 Mbps:** Ask whether the candidate can **upgrade their internet plan** or **switch to a wired connection**. If improvement is possible within 1 week, the candidate may still qualify.

---

## Section 9: Additional Hardware Requirements

### Checklist

- **Operating System:** Windows 10 or Windows 11 (macOS not supported)
- **LAN port:** Must have an Ethernet (RJ-45) port on the PC/laptop
- **Microphone:** Working microphone (for interview; not required for daily work)
- **Webcam:** Not required for the operator role

### Software Requirements (Installed During Training)

- **OBS Studio** or **Streamlabs** (streaming software)
- **Zoom** (for interview and team meetings)
- **Telegram** (primary communication channel)

Candidates do **not** need to install these before the interview. All setup is done during the paid training period.
