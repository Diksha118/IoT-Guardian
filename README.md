# IoT Guardian - Advanced Network Monitoring & Security Suite  

![IoT Guardian Logo](https://via.placeholder.com/150x50?text=IoT+Guardian)  
*Comprehensive protection for your smart devices and network*  

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

### Installation  
```bash  
# Clone repository  
git clone https://github.com/yourusername/iot-guardian.git  
cd iot-guardian  

# Create virtual environment  
python -m venv venv  
source venv/bin/activate  # Linux/MacOS  
venv\Scripts\activate     # Windows  

# Install dependencies  
pip install -r requirements.txt  

# Install system components  
brew install tshark dnctl  # MacOS  
apt install tshark         # Debian/Ubuntu  
