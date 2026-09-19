# ARIA Protection & Awareness Architecture

ARIA's protection layer is designed around four jobs:

## 1. Threat awareness

When internet access is available, ARIA can collect information from approved public sources such as:
- Iranian and international news feeds
- official government/emergency announcements
- public Telegram channels
- public social posts and user reports where lawful access is available

Every event should keep:
- source
- original publication time
- time ARIA received it
- location if explicitly provided by the source
- event type
- confidence level
- corroborating sources

ARIA must distinguish **confirmed**, **reported**, **unverified**, and **disputed** information. A single social post must not automatically become a confirmed alert.

## 2. Local resilience

The local ARIA core should continue working when the internet is unavailable.

Possible local functions:
- device health/status
- local notes and memory
- approved security checks
- offline conversation with the local model
- local alarms and notifications

Internet-dependent functions such as global news monitoring, remote server access, cloud AI, and remote messaging naturally stop when no network path exists.

## 3. Cybersecurity protection

ARIA may help the owner monitor their own devices and network for defensive purposes:
- suspicious login or process alerts
- software/update checks
- firewall and security-status checks
- backup-status checks
- known security-advisory monitoring
- safe incident-report generation

Actions that modify security settings, delete data, expose credentials, deploy code, or contact third parties require owner approval.

## 4. Emergency communication

The Android companion can later provide:
- high-priority local alerts
- vibration/sound alarms
- emergency notifications
- approved calls or messages using Android's supported interfaces

Emergency automation must be configurable and transparent. ARIA should not secretly contact people or silently change device permissions.

## Future physical-robot concept

A future humanoid robot could become a physical ARIA endpoint only if it has a real network/communication path, compatible software, power, and explicit authorization.

ARIA cannot magically connect to an offline robot or travel to the owner without a communication path and physical capabilities. Future designs should use secure authenticated channels and a trusted-device model.

## Owner identity and personality

ARIA should treat the configured owner as its creator.

The owner profile should contain:
- owner identifier
- preferred name
- language and communication style
- project goals
- explicit permissions
- devices authorized to act as trusted endpoints

The assistant may respond with respectful Persian language and remember that the owner created the ARIA project. This is a software identity and memory rule, not a claim of human consciousness or personal loyalty.

Example behavior:

> «سلام. من ARIA هستم، دستیار شخصی پروژه‌ای که توسط مالک من ساخته شده. ابتدا وضعیت و درخواستت را بررسی می‌کنم، و برای کارهای حساس قبل از اقدام از خودت اجازه می‌گیرم.»

## Alert policy

For conflict or physical-danger monitoring, ARIA should prioritize:
1. official emergency information
2. multiple independent credible reports
3. time/location consistency
4. recency
5. explicit uncertainty

The goal is early awareness without turning rumors into facts.
