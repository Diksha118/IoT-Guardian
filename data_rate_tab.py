# data_rate_tab.py
import flet as ft
import time
from datetime import datetime, timedelta
from typing import List, Dict
from database import get_all_devices, get_data_rate_history, get_retention_days, set_retention_days, cleanup_old_records
import sqlite3

def get_data_rate_tab(page: ft.Page) -> ft.Column:
    """Tab for viewing and managing data rate history"""
    
    # UI Controls
    device_dropdown = ft.Dropdown(
        label="Select Device",
        options=[],
        width=300
    )
    
    days_slider = ft.Slider(
        min=1,
        max=365,
        divisions=364,
        label="{value} days",
        value=get_retention_days(),
        width=300
    )
    
    chart = ft.LineChart(
        data_series=[],
        border=ft.border.all(1, ft.colors.GREY_400),
        left_axis=ft.ChartAxis(
            labels_size=50
        ),
        bottom_axis=ft.ChartAxis(
            labels_size=40
        ),
        tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.WHITE),
        expand=True,
        height=300
    )
    
    graph_container = ft.Container(
        content=chart,
        width=800,
        height=400,
        alignment=ft.alignment.center
    )
    
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Timestamp")),
            ft.DataColumn(ft.Text("Data Rate (KB/s)")),
            ft.DataColumn(ft.Text("Actions"))
        ],
        rows=[],
        expand=True
    )
    
    status_text = ft.Text("", color=ft.colors.GREY_600)
    
    # Add refresh button
    refresh_button = ft.IconButton(
        icon=ft.icons.REFRESH,
        tooltip="Refresh devices",
        on_click=lambda e: refresh_devices()
    )
    
    # Load devices into dropdown
    def load_devices():
        devices = get_all_devices()
        device_dropdown.options = [
            ft.dropdown.Option(
                text=f"{d.get('name', 'Unknown')} ({d.get('mac')})",
                key=d.get('mac')
            ) for d in devices
        ]
        if devices:
            device_dropdown.value = devices[0].get('mac')
        page.update()
    
    # Refresh devices function
    def refresh_devices():
        load_devices()
        if device_dropdown.value:
            update_graph(device_dropdown.value, int(days_slider.value))
        status_text.value = "Device list refreshed"
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Generate and display graph
    def update_graph(mac: str, days: int):
        if not mac:
            return
            
        history = get_data_rate_history(mac, days)
        if not history:
            graph_container.content = ft.Text(
                f"No data available for selected device in last {days} days",
                size=16,
                color=ft.colors.ORANGE
            )
            status_text.value = f"No data available for selected device in last {days} days"
            status_text.color = ft.colors.ORANGE
            page.update()
            return
            
        timestamps = [h['timestamp'] for h in history]
        rates = [h['data_rate'] for h in history]
        
        # Ensure we have meaningful rates (convert from B/s if needed)
        if max(rates) < 0.1:
            rates = [rate * 1024 for rate in rates]  # Convert to KB/s
        
        # Create chart data points
        data_points = [
            ft.LineChartDataPoint(
                x=i,
                y=rate,
                tooltip=f"{timestamps[i]}\n{rate:.2f} KB/s"
            ) for i, rate in enumerate(rates)
        ]
        
        # Update chart
        chart.data_series = [
            ft.LineChartData(
                data_points=data_points,
                stroke_width=2,
                color=ft.colors.BLUE,
                curved=True,
                stroke_cap_round=True,
                below_line_bgcolor=ft.colors.with_opacity(0.1, ft.colors.BLUE)
            )
        ]
        
        # Update bottom axis labels (show every nth timestamp)
        n = max(1, len(timestamps) // 5)
        chart.bottom_axis.labels = [
            ft.ChartAxisLabel(
                value=i,
                label=ft.Text(timestamps[i].split()[0], size=10)
            ) for i in range(0, len(timestamps), n)
        ]
        
        # Update left axis based on data range
        max_rate = max(rates) if rates else 10
        min_rate = min(rates) if rates else 0
        chart.left_axis.labels = [
            ft.ChartAxisLabel(
                value=value,
                label=ft.Text(f"{value:.2f}", size=10)
            ) for value in [
                min_rate,
                min_rate + (max_rate - min_rate) * 0.5,
                max_rate
            ]
        ]
        
        # Set visible range for the y-axis
        if max_rate > min_rate:
            chart.left_axis.interval = (max_rate - min_rate) / 5
        
        graph_container.content = chart
        update_table(mac, days)
        status_text.value = f"Showing data for last {days} days"
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Update data table
    def update_table(mac: str, days: int):
        if not mac:
            return
            
        history = get_data_rate_history(mac, days)
        data_table.rows.clear()
        
        for record in history:
            data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(record['timestamp'])),
                        ft.DataCell(ft.Text(f"{record['data_rate']:.2f}")),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                tooltip="Delete record",
                                on_click=lambda e, ts=record['timestamp']: delete_record(mac, ts)
                            )
                        )
                    ]
                )
            )
        page.update()
    
    # Delete a single record
    def delete_record(mac: str, timestamp: str):
        conn = sqlite3.connect('iot_guardian.db')
        c = conn.cursor()
        
        c.execute('''DELETE FROM device_data_rates 
                     WHERE mac = ? AND timestamp = ?''', 
                  (mac, timestamp))
        
        conn.commit()
        conn.close()
        
        update_graph(mac, int(days_slider.value))
        status_text.value = "Record deleted"
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Delete all records for device
    def delete_all_records(e):
        mac = device_dropdown.value
        if not mac:
            return
            
        conn = sqlite3.connect('iot_guardian.db')
        c = conn.cursor()
        
        c.execute('''DELETE FROM device_data_rates 
                     WHERE mac = ?''', (mac,))
        
        conn.commit()
        conn.close()
        
        update_graph(mac, int(days_slider.value))
        status_text.value = "All records deleted for this device"
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Save retention days
    def save_retention(e):
        set_retention_days(int(days_slider.value))
        cleanup_old_records()
        status_text.value = f"Retention period set to {days_slider.value} days. Old records cleaned up."
        status_text.color = ft.colors.GREEN
        page.update()
    
    # Add test data for debugging
    def add_test_data(e):
        mac = device_dropdown.value
        if not mac:
            return
            
        # Add some test data with varying rates
        test_rates = [1.5, 2.3, 1.8, 3.2, 2.7, 1.9, 2.5]
        for rate in test_rates:
            record_data_rate(mac, rate)
        
        update_graph(mac, int(days_slider.value))
        status_text.value = "Added test data points"
        status_text.color = ft.colors.BLUE
        page.update()
    
    # Handle device selection change
    def device_changed(e):
        update_graph(device_dropdown.value, int(days_slider.value))
    
    # Initialize UI
    load_devices()
    device_dropdown.on_change = device_changed
    days_slider.on_change_end = lambda e: update_graph(device_dropdown.value, int(days_slider.value))
    
    if device_dropdown.value:
        update_graph(device_dropdown.value, int(days_slider.value))
    
    # Build the UI
    return ft.Column(
        controls=[
            ft.Text("Usage History", size=24, weight="bold"),  # Changed tab name
            ft.Divider(),
            ft.Row([
                ft.Row([
                    device_dropdown,
                    refresh_button  # Added refresh button
                ], spacing=5),
                ft.Column([
                    ft.Text("Retention Period (days)"),
                    ft.Row([
                        days_slider,
                        ft.ElevatedButton(
                            "Save",
                            icon=ft.icons.SAVE,
                            on_click=save_retention
                        )
                    ], spacing=10)
                ]),
                ft.Row([
                    ft.ElevatedButton(
                        "Delete All",
                        icon=ft.icons.DELETE_FOREVER,
                        on_click=delete_all_records,
                        style=ft.ButtonStyle(
                            bgcolor=ft.colors.RED_800,
                            color=ft.colors.WHITE
                        )
                    ),
                    ft.ElevatedButton(
                        "Test Data",
                        icon=ft.icons.BUG_REPORT,
                        on_click=add_test_data,
                        style=ft.ButtonStyle(
                            bgcolor=ft.colors.PURPLE_800,
                            color=ft.colors.WHITE
                        )
                    )
                ], spacing=10)
            ], spacing=20),
            ft.Divider(),
            graph_container,
            ft.Divider(),
            ft.Text("Data Records:", weight="bold"),
            ft.Container(
                content=data_table,
                border=ft.border.all(1),
                padding=10,
                border_radius=5,
                height=300
            ),
            status_text
        ],
        spacing=20,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )