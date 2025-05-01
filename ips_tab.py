# ips_tab.py
import flet as ft
from database import get_ips_config, update_ips_config, get_device_thresholds, set_device_thresholds, get_ips_events, get_all_devices

def get_ips_tab(page: ft.Page) -> ft.Column:
    """Create the IPS configuration tab with improved UI"""
    
    # Load initial config
    config = get_ips_config()
    
    # UI Controls with better styling
    enabled_switch = ft.Switch(
        value=config['enabled'],
        scale=0.7,  # Makes the switch smaller
        adaptive=True,
    )
    
    switch_row = ft.Row(
        controls=[
            ft.Text("Enable IPS", 
                   size=14,
                   weight="bold",
                   color=ft.colors.BLACK87),  # Darker text
            enabled_switch,
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
    )
    
    throttle_minutes = ft.TextField(
        label="Throttle Duration (minutes)",
        value=str(config['throttle_minutes']),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    email_field = ft.TextField(
        label="Notification Email",
        value=config.get('notification_email', ''),
        width=300,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    phone_field = ft.TextField(
        label="Notification Phone",
        value=config.get('notification_phone', ''),
        width=300,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    device_dropdown = ft.Dropdown(
        label="Select Device",
        options=[],
        width=300,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    max_rate_field = ft.TextField(
        label="Max Data Rate (KB/s)",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    min_rate_field = ft.TextField(
        label="Min Data Rate (KB/s)",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
        border_radius=10,
        filled=True,
        border_color=ft.colors.GREY_400
    )
    
    # Add refresh button
    refresh_button = ft.IconButton(
        icon=ft.icons.REFRESH,
        tooltip="Refresh devices",
        on_click=lambda e: load_devices()
    )
    
    events_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Device", weight="bold")),
            ft.DataColumn(ft.Text("Timestamp", weight="bold")),
            ft.DataColumn(ft.Text("Rate (KB/s)", weight="bold")),
            ft.DataColumn(ft.Text("Action", weight="bold"))
        ],
        rows=[],
        expand=True,
        border=ft.border.all(1, ft.colors.GREY_300),
        border_radius=5
    )
    
    status_text = ft.Text("", color=ft.colors.GREY_600)
    
    # Load devices
    def load_devices():
        devices = get_all_devices()  # Get all devices, not just those with thresholds
        device_dropdown.options = [
            ft.dropdown.Option(
                text=f"{d.get('name', 'Unknown')} ({d['mac']})",
                key=d['mac']
            ) for d in devices
        ]
        if devices:
            device_dropdown.value = devices[0]['mac']
            update_threshold_fields(devices[0]['mac'])
        status_text.value = "Device list refreshed"
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Update threshold fields
    def update_threshold_fields(mac: str):
        thresholds = get_device_thresholds(mac)
        if thresholds:
            max_rate_field.value = str(thresholds[0]['max_data_rate'])
            min_rate_field.value = str(thresholds[0]['min_data_rate'])
        else:
            # Set default values if no thresholds exist
            max_rate_field.value = "100.0"
            min_rate_field.value = "10.0"
        page.update()
    
    # Save IPS config
    def save_config(e):
        try:
            update_ips_config(
                enabled_switch.value,
                int(throttle_minutes.value),
                email_field.value,
                phone_field.value
            )
            status_text.value = "✅ Configuration saved"
            status_text.color = ft.colors.GREEN
        except Exception as e:
            status_text.value = f"❌ Error: {str(e)}"
            status_text.color = ft.colors.RED
        page.update()
    
    # Save device thresholds
    def save_thresholds(e):
        if not device_dropdown.value:
            status_text.value = "❌ Please select a device"
            status_text.color = ft.colors.RED
            page.update()
            return
            
        try:
            set_device_thresholds(
                device_dropdown.value,
                float(max_rate_field.value),
                float(min_rate_field.value)
            )
            status_text.value = "✅ Thresholds saved"
            status_text.color = ft.colors.GREEN
        except Exception as e:
            status_text.value = f"❌ Error: {str(e)}"
            status_text.color = ft.colors.RED
        page.update()
    
    # Load events
    def load_events():
        events = get_ips_events()
        events_table.rows.clear()
        
        for event in events:
            events_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(event['mac'])),
                        ft.DataCell(ft.Text(event['timestamp'])),
                        ft.DataCell(ft.Text(f"{event['detected_rate']:.2f}")),
                        ft.DataCell(ft.Text(event['action_taken']))
                    ]
                )
            )
        page.update()
    
    # Initialize UI
    load_devices()
    load_events()
    device_dropdown.on_change = lambda e: update_threshold_fields(device_dropdown.value)
    
    return ft.Column(
        controls=[
            ft.Text("Intrusion Prevention System", 
                   size=24, 
                   weight="bold",
                   color=ft.colors.BLUE_800),
            ft.Divider(height=10),
            
            # IPS Configuration Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("IPS Configuration", 
                              size=18, 
                              weight="bold",
                              color=ft.colors.BLUE_800),
                        ft.Divider(height=10),
                        switch_row,
                        throttle_minutes,
                        email_field,
                        phone_field,
                        ft.ElevatedButton(
                            "Save Configuration",
                            icon=ft.icons.SAVE,
                            on_click=save_config,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=15,
                                bgcolor=ft.colors.BLUE_600,
                                color=ft.colors.WHITE
                            )
                        )
                    ], spacing=15),
                    padding=20
                ),
                elevation=5,
                margin=ft.margin.symmetric(vertical=10)
            ),
            
            # Device Thresholds Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Device Thresholds", 
                              size=18, 
                              weight="bold",
                              color=ft.colors.BLUE_800),
                        ft.Divider(height=10),
                        ft.Row([
                            ft.Column([
                                ft.Row([
                                    device_dropdown,
                                    refresh_button
                                ], spacing=10),
                            ]),
                            max_rate_field,
                            min_rate_field,
                            ft.ElevatedButton(
                                "Save Thresholds",
                                icon=ft.icons.SAVE,
                                on_click=save_thresholds,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    padding=15,
                                    bgcolor=ft.colors.BLUE_600,
                                    color=ft.colors.WHITE
                                )
                            )
                        ], spacing=20),
                    ], spacing=15),
                    padding=20
                ),
                elevation=5,
                margin=ft.margin.symmetric(vertical=10)
            ),
            
            # Events Section
            ft.Text("Recent Events", 
                   size=18, 
                   weight="bold",
                   color=ft.colors.BLUE_800),
            ft.Container(
                content=ft.Column([
                    events_table,
                    ft.ElevatedButton(
                        "Refresh Events",
                        icon=ft.icons.REFRESH,
                        on_click=lambda e: load_events(),
                        width=200,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=10,
                        )
                    )
                ], spacing=10),
                padding=10,
                border_radius=10,
                border=ft.border.all(1, ft.colors.GREY_300),
                margin=ft.margin.only(top=10)
            ),
            status_text
        ],
        spacing=10,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )