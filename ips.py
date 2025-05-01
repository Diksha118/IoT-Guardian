# ips.py
import threading
import time
import smtplib
from email.mime.text import MIMEText
import subprocess
from database import get_device_thresholds, record_ips_event, get_ips_config
from packet_capture_tab import PacketCapture

class IPSMonitor:
    def __init__(self, page):
        self.page = page
        self.packet_capture = PacketCapture()
        self.running = False
        self.monitor_thread = None

    def start_monitoring(self):
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_devices,
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitor_devices(self):
        while self.running:
            try:
                config = get_ips_config()
                if not config or not config['enabled']:
                    time.sleep(5)
                    continue

                # Check each device's data rate
                devices = get_device_thresholds()
                for device in devices:
                    current_rate = self._get_current_data_rate(device['mac'])
                    if current_rate > device['max_data_rate']:
                        self._handle_anomaly(device, current_rate, config)

                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"IPS monitoring error: {e}")
                time.sleep(10)

    def _get_current_data_rate(self, mac):
        # Implement actual data rate measurement here
        # This is a placeholder - you'd need to implement real measurement
        return 0.0  # Replace with actual measurement

    def _handle_anomaly(self, device, current_rate, config):
        # Log the event
        record_ips_event(
            device['mac'],
            current_rate,
            f"Data rate exceeded threshold ({device['max_data_rate']} KB/s)"
        )

        # Capture traffic for 10 seconds
        capture_thread = threading.Thread(
            target=self._capture_abnormal_traffic,
            args=(device['mac'],),
            daemon=True
        )
        capture_thread.start()

        # Throttle the device
        self._throttle_device(device['mac'], device['min_data_rate'], config['throttle_minutes'])

        # Send notification
        self._send_notification(device, current_rate, config)

    def _capture_abnormal_traffic(self, mac):
        # Capture traffic for 10 seconds
        filename = f"abnormal_{mac}_{int(time.time())}.pcap"
        cmd = [
            "tshark",
            "-i", "bridge100",
            "-a", "duration:10",
            "-w", filename,
            "ether", f"host {mac}"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            record_ips_event(
                mac,
                0,
                f"Traffic capture saved to {filename}"
            )
        except Exception as e:
            record_ips_event(
                mac,
                0,
                f"Failed to capture traffic: {str(e)}"
            )

    def _throttle_device(self, mac, min_rate, throttle_minutes):
        # Implement actual throttling here
        # This is platform-specific - example for macOS:
        try:
            # This is just an example - you'd need real traffic shaping commands
            subprocess.run([
                "sudo", "dnctl", "pipe", "config", "1", 
                f"bw={min_rate}KB/s"
            ], check=True)
            
            record_ips_event(
                mac,
                min_rate,
                f"Throttled to {min_rate} KB/s for {throttle_minutes} minutes"
            )
            
            # Schedule removal of throttle
            threading.Timer(
                throttle_minutes * 60,
                self._remove_throttle,
                args=(mac,)
            ).start()
        except Exception as e:
            record_ips_event(
                mac,
                min_rate,
                f"Failed to throttle: {str(e)}"
            )

    def _remove_throttle(self, mac):
        try:
            subprocess.run(["sudo", "dnctl", "-q", "flush"], check=True)
            record_ips_event(
                mac,
                0,
                "Throttle removed"
            )
        except Exception as e:
            record_ips_event(
                mac,
                0,
                f"Failed to remove throttle: {str(e)}"
            )

    def _send_notification(self, device, current_rate, config):
        message = (
            f"IoT Guardian Alert!\n\n"
            f"Device {device.get('name', 'Unknown')} ({device['mac']}) "
            f"exceeded data rate threshold.\n"
            f"Current rate: {current_rate:.2f} KB/s\n"
            f"Threshold: {device['max_data_rate']} KB/s\n"
            f"Action taken: Throttled to {device['min_data_rate']} KB/s "
            f"for {config['throttle_minutes']} minutes."
        )
        
        # Email notification
        if config.get('notification_email'):
            try:
                msg = MIMEText(message)
                msg['Subject'] = "IoT Guardian IPS Alert"
                msg['From'] = "iot-guardian@yourdomain.com"
                msg['To'] = config['notification_email']
                
                with smtplib.SMTP('localhost') as server:
                    server.send_message(msg)
            except Exception as e:
                print(f"Failed to send email: {e}")

        # TODO: Add phone/SMS notification here