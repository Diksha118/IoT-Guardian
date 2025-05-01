# device_tab.py
import time
import flet as ft
from database import save_device_info, get_device_info
from device_utils import get_connected_devices
from typing import List, Dict

def get_current_devices():
    """Return the current list of connected devices"""
    return connected_devices

# Store reference to connected devices and UI list
connected_devices: List[Dict] = []
device_list_view = ft.Column()

def update_connected_devices(page: ft.Page, devices: List[Dict]):
    """Update the UI with the latest connected devices"""
    global connected_devices
    connected_devices = devices
    
    device_list_view.controls.clear()
    
    if not devices:
        device_list_view.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.WIFI_OFF, size=50, color=ft.colors.GREY_500),
                    ft.Text("No devices connected to hotspot", size=18),
                    ft.FilledButton(
                        "Try Again",
                        icon=ft.icons.REFRESH,
                        on_click=lambda e: refresh_devices(page)
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                padding=40,
                alignment=ft.alignment.center
            )
        )
    else:
        for device in devices:
            device_list_view.controls.append(create_device_card(device, page))
    
    device_list_view.update()

def create_device_card(device: Dict, page: ft.Page) -> ft.Container:
    """Create a UI card for a device with enhanced network info"""
    # Determine connection status icon and color
    connection_status = device.get("status", "Connected")
    if connection_status == "Connected":
        status_icon = ft.Icon(name=ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN)
        status_text = ft.Text("Connected", color=ft.colors.GREEN)
    else:
        status_icon = ft.Icon(name=ft.icons.WARNING, color=ft.colors.ORANGE)
        status_text = ft.Text("Limited Connection", color=ft.colors.ORANGE)
    
    # Network information section
    network_info = ft.Column([
        ft.Row([
            status_icon,
            ft.Text("Network Information", size=16, weight="bold", color="blue900"),
            ft.Container(content=status_text, margin=ft.margin.only(left=10))
        ], spacing=5),
        ft.Divider(height=10, thickness=1),
        ft.Row([
            ft.Column([
                ft.Text("Hostname:", weight="bold", width=100),
                ft.Text("IPv4:", weight="bold", width=100),
                ft.Text("MAC:", weight="bold", width=100),
                ft.Text("Vendor:", weight="bold", width=100)
            ]),
            ft.Column([
                ft.Text(device.get("name", "Unknown")),
                ft.Text(device.get("ipv4", "N/A")),
                ft.Text(device.get("mac", "N/A"), selectable=True),
                ft.Text(device.get("vendor", "Unknown"))
            ])
        ], spacing=20),
        ft.Divider(height=20, thickness=2),
    ], spacing=10)
    
    # Device details section
    name = ft.TextField(
        label="Device Name",
        value=device.get("name", ""),
        filled=True,
        width=300,
        hint_text="e.g. John's iPhone",
        border_radius=10
    )
    
    model = ft.TextField(
        label="Device Model",
        value=device.get("model", ""),
        filled=True,
        width=300,
        hint_text="e.g. iPhone 15 Pro",
        border_radius=10
    )
    
    version = ft.TextField(
        label="OS Version",
        value=device.get("version", ""),
        filled=True,
        width=300,
        hint_text="e.g. iOS 17.4.1",
        border_radius=10
    )
    
    description = ft.TextField(
        label="Description",
        value=device.get("description", ""),
        multiline=True,
        min_lines=2,
        max_lines=4,
        filled=True,
        width=800,
        hint_text="Additional notes about this device",
        border_radius=10
    )

    def save_info(e):
        device["name"] = name.value
        device["model"] = model.value
        device["version"] = version.value
        device["description"] = description.value

    # Save to database
        save_device_info({
        "mac": device.get("mac"),
        "name": name.value,
        "ipv4": device.get("ipv4"),
        "vendor": device.get("vendor"),
        "model": model.value,
        "version": version.value,
        "description": description.value
    })

        save_button.text = "✅ Saved!"
        save_button.icon = ft.icons.CHECK
        page.update()
        
        # Reset button after 2 seconds
        time.sleep(2)
        save_button.text = "Save Device Info"
        save_button.icon = ft.icons.SAVE
        page.update()

    save_button = ft.FilledButton(
        "Save Device Info",
        icon=ft.icons.SAVE,
        on_click=save_info,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=15,
        )
    )

    return ft.Container(
        content=ft.Column([
            ft.Text(f"{device.get('vendor', 'Device')} Details", 
                  size=20, weight="bold", color="blue900"),
            network_info,
            ft.ResponsiveRow(
                [name, model, version], 
                alignment="start",
                run_spacing=10
            ),
            description,
            ft.Container(
                content=save_button,
                alignment=ft.alignment.center_right,
                margin=ft.margin.only(top=15)
            )
        ], spacing=20),
        padding=25,
        margin=10,
        border_radius=20,
        bgcolor=ft.colors.BLUE_50,
        border=ft.border.all(1, ft.colors.BLUE_100),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.colors.GREY_300,
            offset=ft.Offset(0, 3)
        ),
        width=900
    )

def get_device_tab(page: ft.Page) -> ft.Column:
    """Create the device management tab"""
    search_box = ft.TextField(
        label="🔍 Search Devices",
        width=400,
        hint_text="Search by name, IP, or MAC",
        border_radius=10,
        filled=True,
        on_change=lambda e: apply_filter(page, search_box.value)
    )

    refresh_btn = ft.FilledButton(
        "Refresh Devices",
        icon=ft.icons.REFRESH,
        on_click=lambda e: refresh_devices(page),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=15,
        ),
        tooltip="Scan network for connected devices"
    )

    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.icons.NETWORK_WIFI, size=30, color="indigo600"),
            ft.Text("Connected Devices", size=24, weight="bold", color="indigo600"),
            ft.Row([search_box, refresh_btn], spacing=15)
        ], 
        alignment="spaceBetween",
        vertical_alignment="center"),
        padding=ft.padding.symmetric(vertical=15),
        margin=ft.margin.only(bottom=20)
    )

    layout = ft.Column(
        controls=[header, device_list_view],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    return layout

def apply_filter(page: ft.Page, query: str):
    """Filter devices based on search query"""
    if not query:
        update_connected_devices(page, connected_devices)
        return
        
    query = query.lower()
    filtered = [
        d for d in connected_devices 
        if (query in d.get("name", "").lower() or 
            query in d.get("ipv4", "").lower() or 
            query in d.get("mac", "").lower() or 
            query in d.get("vendor", "").lower())
    ]
    update_connected_devices(page, filtered)

def refresh_devices(page: ft.Page):
    """Refresh the list of connected devices"""
    # Show loading indicator
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.ProgressRing(width=20, height=20, stroke_width=2),
            ft.Text(" Scanning network for devices...", size=14)
        ], spacing=15),
        open=True,
        duration=2000
    )
    page.update()
    
    try:
        new_devices = get_connected_devices()
        update_connected_devices(page, new_devices)
        
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"✅ Found {len(new_devices)} device(s)"),
            open=True,
            duration=3000
        )
    except Exception as e:
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"⚠️ Error scanning devices: {str(e)}"),
            open=True,
            bgcolor=ft.colors.RED_400
        )
    finally:
        page.update()