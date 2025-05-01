# IoT Guardian

## Overview

IoT Guardian is a comprehensive network monitoring and security application designed specifically for IoT environments. It provides real-time device monitoring, intrusion prevention, firewall management, and packet capture capabilities to help secure your IoT network.

## 🌟 Key Features  

| Feature | Description |  
|---------|-------------|  
| **📋 Device Manager** | Auto-discovery of all connected devices with detailed profiles |  
| **📊 Usage Analytics** | Real-time and historical data rate monitoring with interactive charts |  
| **🛡️ Smart Firewall** | Rule-based traffic filtering with domain/IP/port blocking |  
| **🚨 IPS Engine** | Anomaly detection with automatic throttling and alerts |  
| **🛰 Packet Inspector** | Advanced traffic capture and analysis with TShark integration |  
| **📈 Database Explorer** | Direct access to all collected network data |  

## 🚀 Getting Started  

### Prerequisites  
- Python 3.8+  
- macOS/Linux (Windows support experimental)  
- Root privileges for full functionality  

### 💻 Installation  
```bash  
# Clone repository  
git clone https://github.com/yourusername/iot-guardian.git  
cd iot-guardian  

# Create virtual environment  
python -m venv venv  
source venv/bin/activate  # Linux/MacOS  
venv\Scripts\activate     # Windows  
```

### Requirements
```bash  
# Core dependencies
python>=3.8
flet>=0.9.0
tshark>=3.6.0
sqlite3>=3.35.0

# On Debian/Ubuntu
sudo apt install tshark sqlite3

# On macOS
brew install wireshark
Setup
bash
git clone https://github.com/yourrepo/iot-guardian.git
cd iot-guardian
python -m pip install -r requirements.txt

# Initialize database
python -c "from database import init_db; init_db()"
```
