# NoSQL Injection Lab Exploits

Cyber Offense and Defense Course Project - Automated exploitation tools for PortSwigger NoSQL Injection labs.

## Overview

This repository contains Python scripts for solving three PortSwigger Web Security Academy labs focused on NoSQL injection vulnerabilities.

## Repository Structure
```
.
├── script/                    # Basic implementations with colorama
│   ├── lab1.py                # Authentication bypass exploit
│   ├── lab2.py                # Password extraction exploit
│   └── lab3.py                # Token enumeration exploit
│   └── requirements.txt       # Dependencies
│
├── rich-script/               # Enhanced versions with Rich library + Typer CLI
│   ├── lab1.py                # Interactive auth bypass with exploration mode
│   ├── lab2.py                # Progress-tracked password extraction
│   └── lab3.py                # Matrix-style visual token cracker
│   └── requirements.txt       # Dependencies
│
├── presentazione/  # Presentation slides
│   ├── ITA/       # Italian version
│   └── ENG/       # English version
│
└── demo/          # Video demonstrations
```

## Quick Start

### Prerequisites
```bash
# Nella cartella rich-script o script, in base a cosa si vuole eseguire
pip install -r requirements.txt

```

### Usage

#### Basic Scripts
```bash
# Edit LAB_ID in the script first
python script/lab1.py
python script/lab2.py
python script/lab3.py
```

#### Enhanced Scripts (CLI)
```bash
# Direct execution
python rich-script/lab1.py YOUR_LAB_ID

# With exploration mode (lab1 only)
python rich-script/lab1.py YOUR_LAB_ID --explore
```

## Labs Covered

| Lab | Description | Link |
|-----|-------------|------|
| Lab 1 | Authentication Bypass | [PortSwigger](https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-bypass-authentication) |
| Lab 2 | Data Extraction | [PortSwigger](https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-data) |
| Lab 3 | Field Enumeration | [PortSwigger](https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-bypass-authentication) |

## Presentations

Complete project presentations available:

- 🇮🇹 **Italian**: [Canva Presentation](https://www.canva.com/design/DAG5P7-Cd44/EcAW_lym0FiwCvJI5yXKYg/edit?utm_content=DAG5P7-Cd44&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)
- 🇬🇧 **English**: [Canva Presentation](https://www.canva.com/design/DAG7lRY8FxM/5pYHsYhmQh1hnoVRSrWvog/edit?utm_content=DAG7lRY8FxM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

## Video Demonstrations

The `demo/` folder contains screen recordings showing real-time exploit execution.

---

**Course**: Cyber Offense and Defense  
**Academic Year**: 2024/2025
