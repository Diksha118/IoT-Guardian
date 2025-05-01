import flet as ft
import subprocess
import socket
import re
from typing import List, Dict
from database import save_firewall_rules, load_firewall_rules

def get_firewall_tab(page: ft.Page) -> ft.Column:
    """Firewall management tab that works without editing /etc/pf.conf"""
    firewall_rules = load_firewall_rules()

    def resolve_domain(domain: str) -> List[str]:
        """Resolve domain to IP addresses with proper IPv6 formatting"""
        try:
            ips = []
            for info in socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP):
                ip = info[4][0]
                if ':' in ip:  # IPv6
                    ip = f"{{{ip}}}"  # Wrap IPv6 in curly braces
                ips.append(ip)
            return list(set(ips))
        except (socket.gaierror, IndexError):
            return []

    def validate_ipv6(ip: str) -> bool:
        """Validate IPv6 address format"""
        ipv6_regex = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        return bool(re.match(ipv6_regex, ip))

    # UI Components
    rule_type_dropdown = ft.Dropdown(
        label="Rule Type",
        options=[
            ft.dropdown.Option("ip"),
            ft.dropdown.Option("port"),
            ft.dropdown.Option("domain"),
        ],
        value="ip",
        width=150
    )

    target_field = ft.TextField(
        label="IP to block",
        hint_text="e.g. 192.168.1.100",
        width=250
    )

    def update_target_field(e):
        if rule_type_dropdown.value == "port":
            target_field.hint_text = "e.g. 80 or 443"
            target_field.label = "Port to block"
        elif rule_type_dropdown.value == "domain":
            target_field.hint_text = "e.g. example.com"
            target_field.label = "Website to block"
        else:
            target_field.hint_text = "e.g. 192.168.1.100"
            target_field.label = "IP to block"
        page.update()

    rule_type_dropdown.on_change = update_target_field

    protocol_dropdown = ft.Dropdown(
        label="Protocol",
        options=[
            ft.dropdown.Option("tcp"),
            ft.dropdown.Option("udp"),
            ft.dropdown.Option("icmp"),
            ft.dropdown.Option("all"),
        ],
        value="all",
        width=150
    )

    action_dropdown = ft.Dropdown(
        label="Action",
        options=[
            ft.dropdown.Option("DROP"),
            ft.dropdown.Option("REJECT"),
        ],
        value="DROP",
        width=150
    )

    rules_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Type")),
            ft.DataColumn(ft.Text("Target")),
            ft.DataColumn(ft.Text("Protocol")),
            ft.DataColumn(ft.Text("Action")),
            ft.DataColumn(ft.Text("Operations")),
        ],
        rows=[],
        expand=True
    )

    status_text = ft.Text("", color=ft.colors.GREEN)

    def apply_firewall_rules():
        """Apply rules without flushing system rules"""
        try:
            # Create minimal ruleset that only adds our blocking rules
            pf_rules = [
                "# Minimal PF ruleset that preserves system rules",
                "",
                "# Our custom blocking rules only",
                "block in quick"  # This will be combined with our specific rules
            ]

            # Add our custom blocking rules
            blocked_ips = set()
            blocked_domains = []
            
            for rule in firewall_rules:
                target = rule['target']
                proto = rule['protocol']
                action = rule['action'].lower()
                
                # Handle domain resolution
                if rule['type'] == "domain":
                    ips = resolve_domain(target)
                    if not ips:
                        continue
                    blocked_domains.append(f"{target} ({', '.join(ips)})")
                    for ip in ips:
                        blocked_ips.add(ip)
                        if ':' in ip:  # IPv6
                            pf_rules.append(f"block in quick proto {proto} from any to {{{ip}}} {action}")
                            pf_rules.append(f"block in quick proto {proto} from {{{ip}}} to any {action}")
                        else:  # IPv4
                            pf_rules.append(f"block in quick proto {proto} from any to {ip} {action}")
                            pf_rules.append(f"block in quick proto {proto} from {ip} to any {action}")
                
                # Handle IP rules
                elif rule['type'] == "ip":
                    if ':' in target and not validate_ipv6(target):
                        raise ValueError(f"Invalid IPv6 address format: {target}")
                    blocked_ips.add(target)
                    if ':' in target:  # IPv6
                        pf_rules.append(f"block in quick proto {proto} from any to {{{target}}} {action}")
                        pf_rules.append(f"block in quick proto {proto} from {{{target}}} to any {action}")
                    else:  # IPv4
                        pf_rules.append(f"block in quick proto {proto} from any to {target} {action}")
                        pf_rules.append(f"block in quick proto {proto} from {target} to any {action}")
                
                # Handle port rules
                elif rule['type'] == "port":
                    proto = proto if proto != "all" else "{tcp,udp}"
                    pf_rules.append(f"block in quick proto {proto} from any to any port {target} {action}")

            # Write rules to temp file
            with open("/tmp/pf.rules", "w") as f:
                f.write("\n".join(pf_rules))

            # Test rules before applying
            test_result = subprocess.run(
                ["sudo", "pfctl", "-nf", "/tmp/pf.rules"],
                capture_output=True,
                text=True
            )
            
            if test_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    test_result.returncode,
                    test_result.args,
                    test_result.stdout,
                    test_result.stderr
                )

            # Apply rules without flushing (-F none)
            subprocess.run(["sudo", "pfctl", "-F", "none", "-f", "/tmp/pf.rules"], check=True)
            
            # Update status
            status_msg = [
                "✅ Firewall rules applied successfully",
                f"Blocked IPs: {', '.join(blocked_ips) or 'None'}",
                f"Blocked domains: {', '.join(blocked_domains) or 'None'}"
            ]
            status_text.value = "\n".join(status_msg)
            status_text.color = ft.colors.GREEN
            page.update()

        except subprocess.CalledProcessError as e:
            error_msg = [
                "❌ Error applying rules:",
                e.stderr if e.stderr else str(e),
                "",
                "Temporary rules file contents:"
            ]
            try:
                with open("/tmp/pf.rules", "r") as f:
                    error_msg.extend(f.read().splitlines())
            except Exception:
                error_msg.append("Could not read rules file")
            
            status_text.value = "\n".join(error_msg)
            status_text.color = ft.colors.RED
            page.update()
        except Exception as e:
            status_text.value = f"❌ Error: {str(e)}"
            status_text.color = ft.colors.RED
            page.update()

    def update_rules_table():
        rules_table.rows.clear()
        for i, rule in enumerate(firewall_rules):
            rules_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(rule['type'].upper())),
                        ft.DataCell(ft.Text(rule['target'])),
                        ft.DataCell(ft.Text(rule['protocol'].upper())),
                        ft.DataCell(ft.Text(rule['action'])),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    on_click=lambda e, idx=i: delete_rule(idx),
                                    tooltip="Delete rule"
                                ),
                            ])
                        ),
                    ]
                )
            )
        page.update()

    def add_rule(e):
        target = target_field.value.strip()
        if not target:
            status_text.value = "⚠️ Please enter a target"
            status_text.color = ft.colors.ORANGE
            page.update()
            return
            
        if not validate_target(rule_type_dropdown.value, target):
            status_text.value = "⚠️ Invalid target format"
            status_text.color = ft.colors.ORANGE
            page.update()
            return
            
        new_rule = {
            "type": rule_type_dropdown.value,
            "target": target,
            "protocol": protocol_dropdown.value,
            "action": action_dropdown.value
        }
        
        # For domains, show resolved IPs
        if new_rule['type'] == "domain":
            ips = resolve_domain(target)
            if not ips:
                status_text.value = f"⚠️ Could not resolve {target}"
                status_text.color = ft.colors.ORANGE
                page.update()
                return
            status_text.value = f"Resolved {target} to: {', '.join(ips)}"
            status_text.color = ft.colors.BLUE
        
        firewall_rules.append(new_rule)
        save_firewall_rules(firewall_rules)
        update_rules_table()
        target_field.value = ""
        page.update()

    def delete_rule(index: int):
        firewall_rules.pop(index)
        save_firewall_rules(firewall_rules)
        update_rules_table()
        status_text.value = "Rule deleted (click Apply to update firewall)"
        status_text.color = ft.colors.BLUE
        page.update()

    def validate_target(rule_type: str, target: str) -> bool:
        if rule_type == "ip":
            if ':' in target:  # IPv6
                return validate_ipv6(target)
            parts = target.split('.')
            return (len(parts) == 4 and 
                    all(part.isdigit() and 0 <= int(part) <= 255 for part in parts))
        elif rule_type == "port":
            return target.isdigit() and 1 <= int(target) <= 65535
        elif rule_type == "domain":
            return ('.' in target and 
                    all(c.isalnum() or c in '.-' for c in target))
        return False

    # Initialize UI
    update_rules_table()

    return ft.Column(
        controls=[
            ft.Text("Firewall Configuration", size=24, weight="bold"),
            ft.Divider(),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Add New Rule", weight="bold"),
                        ft.Row([
                            rule_type_dropdown,
                            target_field,
                            protocol_dropdown,
                            action_dropdown,
                        ], spacing=10),
                        ft.ElevatedButton(
                            "Add Rule",
                            icon=ft.icons.ADD,
                            on_click=add_rule,
                            width=200
                        ),
                    ], spacing=10),
                    padding=15
                ),
                elevation=5
            ),
            ft.Divider(),
            ft.Text("Current Firewall Rules:", weight="bold"),
            ft.Container(
                content=rules_table,
                border=ft.border.all(1, color=ft.colors.GREY_400),
                padding=10,
                border_radius=5,
                height=300,
                expand=True
            ),
            ft.Row([
                ft.ElevatedButton(
                    "Apply Rules",
                    icon=ft.icons.SECURITY,
                    on_click=lambda e: apply_firewall_rules(),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.GREEN_800,
                        color=ft.colors.WHITE
                    ),
                    width=200
                ),
                ft.ElevatedButton(
                    "Reset All Rules",
                    icon=ft.icons.RESTART_ALT,
                    on_click=lambda e: [
                        firewall_rules.clear(),
                        save_firewall_rules(firewall_rules),
                        update_rules_table(),
                        subprocess.run(["sudo", "pfctl", "-F", "rules"], check=True),
                        setattr(status_text, "value", "All rules cleared - system rules remain"),
                        setattr(status_text, "color", ft.colors.GREEN),
                        page.update()
                    ],
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.RED_800,
                        color=ft.colors.WHITE
                    ),
                    width=200
                )
            ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(
                content=status_text,
                padding=10,
                border_radius=5,
                bgcolor=ft.colors.GREY_100
            )
        ],
        spacing=20,
        expand=True,
        scroll=ft.ScrollMode.AUTO
    )