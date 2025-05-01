import flet as ft
from device_tab import get_device_tab, refresh_devices
from packet_capture_tab import get_packet_capture_tab
from firewall_tab import get_firewall_tab
from database import get_database_tables, get_table_data
from data_rate_tab import get_data_rate_tab
import database  # This will initialize the database
from ips_tab import get_ips_tab
from ips import IPSMonitor

def get_database_viewer_tab(page: ft.Page) -> ft.Column:
    """Create the database viewer tab content"""
    # UI Components
    table_dropdown = ft.Dropdown(
        label="Select Table",
        width=300,
        options=[],
        autofocus=True
    )
    
    data_table = ft.DataTable(
        columns=[],
        rows=[],
        expand=True
    )
    
    status_text = ft.Text("", color=ft.colors.GREY_600)
    
    # Load available tables
    def load_tables():
        try:
            tables = get_database_tables()
            table_dropdown.options = [
                ft.dropdown.Option(table['name']) for table in tables
            ]
            if tables:
                table_dropdown.value = tables[0]['name']
                load_table_data(None)
            page.update()
        except Exception as e:
            status_text.value = f"Error loading tables: {str(e)}"
            status_text.color = ft.colors.RED
            page.update()
    
    # Load data from selected table
    def load_table_data(e):
        if table_dropdown.value:
            try:
                data = get_table_data(table_dropdown.value)
                
                # Create columns
                if data and len(data) > 0:
                    columns = list(data[0].keys())
                    data_table.columns = [
                        ft.DataColumn(ft.Text(col, weight="bold")) 
                        for col in columns
                    ]
                    
                    # Create rows
                    data_table.rows = [
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(row[col])))
                                for col in columns
                            ]
                        )
                        for row in data
                    ]
                    
                    status_text.value = f"Showing {len(data)} rows from '{table_dropdown.value}'"
                    status_text.color = ft.colors.GREEN
                else:
                    data_table.columns = []
                    data_table.rows = []
                    status_text.value = f"Table '{table_dropdown.value}' is empty"
                    status_text.color = ft.colors.ORANGE
            except Exception as e:
                status_text.value = f"Error loading table: {str(e)}"
                status_text.color = ft.colors.RED
            finally:
                page.update()
    
    table_dropdown.on_change = load_table_data
    
    # Initial load
    load_tables()
    
    # Build the UI
    return ft.Column(
        controls=[
            ft.Text("Database Viewer", size=24, weight="bold"),
            ft.Divider(),
            ft.Row([
                table_dropdown,
                ft.ElevatedButton(
                    "Refresh Data",
                    icon=ft.icons.REFRESH,
                    on_click=load_table_data
                )
            ], spacing=20),
            ft.Divider(),
            ft.Container(
                content=data_table,
                border=ft.border.all(1),
                padding=10,
                border_radius=5,
                expand=True,
                height=400
            ),
            status_text
        ],
        spacing=20,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )

def main(page: ft.Page):
    # Cleanup old records on startup
    database.cleanup_old_records()

    # App configuration
    page.title = "🔧 IoT Guardian"
    page.window_width = 1280
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 30
    page.scroll = ft.ScrollMode.AUTO

    # AppBar setup
    page.appbar = ft.AppBar(
        title=ft.Text("IoT Guardian", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
        bgcolor=ft.colors.BLUE_800,
        center_title=False,
        leading=ft.Icon(name=ft.icons.ROUTER, color=ft.colors.WHITE),
        actions=[
            ft.IconButton(
                icon=ft.icons.SETTINGS,
                icon_color=ft.colors.WHITE,
                tooltip="Settings"
            ),
            ft.IconButton(
                icon=ft.icons.LOGOUT,
                icon_color=ft.colors.WHITE,
                tooltip="Logout"
            )
        ]
    )

    # Create tabs
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="📋 Device Manager", content=get_device_tab(page)),
            ft.Tab(text="📊 Usage History", content=get_data_rate_tab(page)),
            ft.Tab(text="🛰 Packet Capture", content=get_packet_capture_tab(page)),
            ft.Tab(text="🛡️ Firewall", content=get_firewall_tab(page)),
            ft.Tab(text="🚨 IPS", content=get_ips_tab(page)),
            ft.Tab(text="🗃️ Database Viewer", content=get_database_viewer_tab(page)),
        ],
        expand=True
    )

    # Add tabs to page
    page.add(tabs)

    # Initialize and start IPS monitor
    ips_monitor = IPSMonitor(page)
    ips_monitor.start_monitoring()

    # Initial device scan
    refresh_devices(page)

ft.app(target=main)