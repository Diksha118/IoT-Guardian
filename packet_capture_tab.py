import flet as ft
import subprocess
import time
import threading
import os
from typing import Dict, List
from device_tab import get_current_devices
from database import record_data_rate

class PacketCapture:
    def __init__(self):
        self.active_captures: Dict[str, subprocess.Popen] = {}
        self.capture_threads: Dict[str, threading.Thread] = {}
        self.start_times: Dict[str, float] = {}

def get_packet_capture_tab(page: ft.Page) -> ft.Column:
    """Packet capture tab with device selection, duration options, and start/stop controls"""
    pc = PacketCapture()
    
    # UI Controls
    duration_field = ft.TextField(
        label="Duration (seconds)",
        width=200,
        keyboard_type=ft.KeyboardType.NUMBER,
        hint_text="0 for continuous",
        value="20"
    )
    
    filename_field = ft.TextField(
        label="Filename Pattern",
        value="capture_{device}_{time}",
        width=300
    )
    
    device_dropdown = ft.Dropdown(
        label="Select Device",
        width=300,
        options=[]
    )
    
    output_text = ft.Text("", selectable=True)
    capture_progress = ft.ProgressBar(width=400, visible=False)
    status_text = ft.Text("Ready", color=ft.colors.GREY_600)
    
    # Buttons
    start_btn = ft.ElevatedButton(
        "Start Capture",
        icon=ft.icons.PLAY_ARROW,
        on_click=lambda e: start_capture(),
        width=150,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.GREEN_800,
            color=ft.colors.WHITE
        )
    )
    
    stop_btn = ft.ElevatedButton(
        "Stop Capture",
        icon=ft.icons.STOP,
        on_click=lambda e: stop_capture(),
        width=150,
        style=ft.ButtonStyle(
            bgcolor=ft.colors.RED_800,
            color=ft.colors.WHITE
        ),
        disabled=True
    )
    
    refresh_btn = ft.IconButton(
        icon=ft.icons.REFRESH,
        on_click=lambda e: update_device_list(),
        tooltip="Refresh devices"
    )
    
    # Update device dropdown
    def update_device_list():
        devices = get_current_devices()
        device_dropdown.options = [
            ft.dropdown.Option(
                text=f"{d.get('name', 'Unknown')} ({d.get('mac', 'N/A')})",
                key=d.get('mac')
            ) for d in devices
        ]
        if devices:
            device_dropdown.value = devices[0].get('mac')
        page.update()
    
    # Run tshark command
    def run_tshark(mac: str, duration: int):
        device = next((d for d in get_current_devices() if d.get('mac') == mac), None)
        if not device:
            return
            
        name = device.get("name", "Unknown")
        filename = filename_field.value.format(
            device=name.replace(" ", "_"),
            time=int(time.time())
        ) + ".pcap"
        
        cmd = [
            "tshark",
            "-i", "bridge100",
            *(["-a", f"duration:{duration}"] if duration > 0 else []),
            "-w", filename,
            "ether", f"host {mac}"
        ]
        
        try:
            pc.start_times[mac] = time.time()
            output_text.value += f"\n🚀 Starting capture for {name} ({mac})...\n"
            output_text.value += f"📁 File: {filename}\n"
            output_text.value += f"⏱️ Duration: {'Continuous' if duration == 0 else f'{duration} seconds'}\n"
            page.update()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            pc.active_captures[mac] = process
            update_ui_state("Capture started")
            
            # Read output in real-time
            while process.poll() is None:
                output = process.stdout.readline()
                if output:
                    output_text.value += output
                    page.update()
                time.sleep(0.1)
            
            # Calculate data rate if completed normally
            if process.returncode == 0 and os.path.exists(filename):
                file_size_kb = os.path.getsize(filename) / 1024
                actual_duration = duration if duration > 0 else (time.time() - pc.start_times[mac])
                data_rate = file_size_kb / actual_duration
                record_data_rate(mac, data_rate)
                output_text.value += f"\n✅ Capture completed for {name}\n"
                output_text.value += f"💾 Saved to: {filename}\n"
                output_text.value += f"📊 Data rate: {data_rate:.2f} KB/s\n"
                output_text.value += f"⏱️ Actual duration: {actual_duration:.1f} seconds\n"
            
        except Exception as e:
            output_text.value += f"\n❌ Error capturing {name}: {str(e)}\n"
        finally:
            if mac in pc.active_captures:
                pc.active_captures.pop(mac)
            if mac in pc.start_times:
                pc.start_times.pop(mac)
            update_ui_state("Ready")
            page.update()
    
    # Start capture
    def start_capture():
        if not device_dropdown.value:
            update_ui_state("No device selected")
            return
            
        mac = device_dropdown.value
        try:
            duration = int(duration_field.value) if duration_field.value else 0
            if duration < 0:
                duration = 0
        except ValueError:
            duration = 0
            
        if mac in pc.active_captures:
            update_ui_state("Capture already running")
            return
            
        thread = threading.Thread(
            target=run_tshark,
            args=(mac, duration),
            daemon=True
        )
        thread.start()
        
        pc.capture_threads[mac] = thread
        update_ui_state("Capture running")
    
    # Stop capture
    def stop_capture():
        if not device_dropdown.value:
            return
            
        mac = device_dropdown.value
        if mac in pc.active_captures:
            try:
                pc.active_captures[mac].terminate()
                output_text.value += f"\n🛑 Capture stopped for device {mac}\n"
                
                # Calculate partial data if stopped manually
                if mac in pc.start_times and os.path.exists(filename):
                    filename = filename_field.value.format(
                        device=next((d.get('name', 'Unknown').replace(" ", "_") 
                                   for d in get_current_devices() 
                                   if d.get('mac') == mac), "Unknown"),
                        time=int(pc.start_times[mac])
                    ) + ".pcap"
                    
                    if os.path.exists(filename):
                        file_size_kb = os.path.getsize(filename) / 1024
                        actual_duration = time.time() - pc.start_times[mac]
                        data_rate = file_size_kb / actual_duration
                        record_data_rate(mac, data_rate)
                        output_text.value += f"📊 Partial data rate: {data_rate:.2f} KB/s\n"
                        output_text.value += f"⏱️ Duration: {actual_duration:.1f} seconds\n"
                
            except Exception as e:
                output_text.value += f"\n⚠️ Error stopping capture: {str(e)}\n"
        
        update_ui_state("Capture stopped")
    
    # Update UI state
    def update_ui_state(message: str = None):
        mac = device_dropdown.value
        is_active = mac in pc.active_captures
        
        start_btn.disabled = is_active or not mac
        stop_btn.disabled = not is_active
        device_dropdown.disabled = is_active
        capture_progress.visible = is_active
        
        if message:
            status_text.value = message
            status_text.color = ft.colors.GREEN if "start" in message.lower() else (
                ft.colors.RED if "stop" in message.lower() else ft.colors.BLUE
            )
        
        page.update()
    
    # Initialize UI
    update_device_list()
    device_dropdown.on_change = lambda e: update_ui_state()
    
    # Build the UI
    return ft.Column(
        controls=[
            ft.Text("Packet Capture", size=24, weight="bold"),
            ft.Divider(),
            ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text("Select Device:", weight="bold", size=16),
                        refresh_btn
                    ]),
                    device_dropdown,
                    ft.Divider(),
                    ft.Text("Capture Settings:", weight="bold", size=16),
                    duration_field,
                    filename_field,
                    ft.Row([
                        start_btn,
                        stop_btn,
                    ], spacing=20),
                    capture_progress,
                    status_text
                ], width=350),
                ft.VerticalDivider(width=1),
                ft.Column([
                    ft.Text("Capture Output:", weight="bold", size=16),
                    ft.Container(
                        content=output_text,
                        border=ft.border.all(1),
                        padding=10,
                        border_radius=5,
                        expand=True,
                        height=500
                    )
                ], expand=True)
            ], spacing=20, expand=True)
        ],
        spacing=20,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )