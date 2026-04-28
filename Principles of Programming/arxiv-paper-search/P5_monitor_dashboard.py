#!/usr/bin/env python3
"""
Monitoring Dashboard for arXiv Newsletter Automation

This script provides a simple text-based dashboard to monitor the
automation system's health and activity.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "automation_config.json"


def load_config() -> dict[str, Any] | None:
    """Load configuration file."""
    if not CONFIG_FILE.exists():
        return None
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_latest_newsletter_info() -> dict[str, Any] | None:
    """Get information about the latest newsletter."""
    latest_html = OUTPUT_DIR / "newsletter_latest.html"
    
    if not latest_html.exists():
        return None
    
    stat = latest_html.stat()
    return {
        "path": latest_html,
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime),
    }


def get_newsletter_history() -> list[dict[str, Any]]:
    """Get list of all newsletters."""
    newsletters = []
    
    for newsletter in sorted(OUTPUT_DIR.glob("newsletter_*.html"), reverse=True):
        if newsletter.name == "newsletter_latest.html":
            continue
        
        stat = newsletter.stat()
        newsletters.append({
            "name": newsletter.name,
            "path": newsletter,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
        })
    
    return newsletters[:10]  # Last 10 newsletters


def parse_log_stats(log_file: Path) -> dict[str, Any]:
    """Parse log file and extract statistics."""
    if not log_file.exists():
        return {}
    
    stats = {
        "total_lines": 0,
        "errors": 0,
        "warnings": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "last_run": None,
    }
    
    with log_file.open("r", encoding="utf-8") as f:
        for line in f:
            stats["total_lines"] += 1
            
            if "ERROR" in line:
                stats["errors"] += 1
            if "WARNING" in line:
                stats["warnings"] += 1
            if "✓ Newsletter sent successfully" in line:
                stats["successful_runs"] += 1
            if "✗ Failed to send newsletter" in line:
                stats["failed_runs"] += 1
            
            # Try to extract timestamp from last line
            if line.strip():
                try:
                    # Format: 2026-04-21 09:00:00 - INFO - Message
                    timestamp_str = line.split(" - ")[0]
                    stats["last_run"] = datetime.strptime(
                        timestamp_str, "%Y-%m-%d %H:%M:%S"
                    )
                except:
                    pass
    
    return stats


def get_current_month_log() -> Path:
    """Get the current month's log file path."""
    current_month = datetime.now().strftime("%Y%m")
    return LOG_DIR / f"automation_{current_month}.log"


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'X hours/days ago'."""
    now = datetime.now()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"


def print_dashboard() -> None:
    """Print the monitoring dashboard."""
    print("=" * 80)
    print("📊 arXiv Newsletter Automation - Monitoring Dashboard")
    print("=" * 80)
    print()
    
    # Configuration Status
    print("⚙️  Configuration Status")
    print("-" * 80)
    config = load_config()
    if config:
        print(f"✓ Config file found: {CONFIG_FILE}")
        
        email_config = config.get("email", {})
        sender = email_config.get("sender_email", "Not configured")
        recipients = email_config.get("recipients", [])
        print(f"  Sender: {sender}")
        print(f"  Recipients: {len(recipients)} email(s)")
        
        schedule_config = config.get("schedule", {})
        day = schedule_config.get("day_of_week", "Not set")
        time = schedule_config.get("time", "Not set")
        print(f"  Schedule: {day.capitalize()} at {time}")
        
        search_config = config.get("search", {})
        queries = search_config.get("default_queries", [])
        model = search_config.get("ollama_model", "Not set")
        print(f"  Queries: {len(queries)} topic(s)")
        print(f"  Model: {model}")
    else:
        print(f"✗ Config file not found: {CONFIG_FILE}")
        print("  Run: python arxiv_automation.py --create-config")
    print()
    
    # Latest Newsletter
    print("📰 Latest Newsletter")
    print("-" * 80)
    latest = get_latest_newsletter_info()
    if latest:
        print(f"✓ Newsletter generated")
        print(f"  File: {latest['path'].name}")
        print(f"  Size: {format_size(latest['size'])}")
        print(f"  Modified: {latest['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Age: {format_time_ago(latest['modified'])}")
    else:
        print("✗ No newsletter found")
        print("  Run: python arxiv_automation.py --run-now")
    print()
    
    # Newsletter History
    print("📚 Newsletter History (Last 10)")
    print("-" * 80)
    history = get_newsletter_history()
    if history:
        for i, newsletter in enumerate(history, 1):
            created_str = newsletter["created"].strftime("%Y-%m-%d %H:%M")
            size_str = format_size(newsletter["size"])
            print(f"  {i:2d}. {newsletter['name']}")
            print(f"      Created: {created_str} | Size: {size_str}")
    else:
        print("  No newsletter history found")
    print()
    
    # Log Statistics
    print("📝 Log Statistics (Current Month)")
    print("-" * 80)
    log_file = get_current_month_log()
    if log_file.exists():
        stats = parse_log_stats(log_file)
        print(f"✓ Log file: {log_file.name}")
        print(f"  Total lines: {stats['total_lines']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Warnings: {stats['warnings']}")
        print(f"  Successful runs: {stats['successful_runs']}")
        print(f"  Failed runs: {stats['failed_runs']}")
        if stats['last_run']:
            print(f"  Last activity: {stats['last_run'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  ({format_time_ago(stats['last_run'])})")
    else:
        print(f"✗ No log file found: {log_file.name}")
    print()
    
    # Disk Usage
    print("💾 Disk Usage")
    print("-" * 80)
    
    if OUTPUT_DIR.exists():
        output_size = sum(f.stat().st_size for f in OUTPUT_DIR.rglob("*") if f.is_file())
        output_count = len(list(OUTPUT_DIR.rglob("*")))
        print(f"  Output directory: {format_size(output_size)} ({output_count} files)")
    else:
        print(f"  Output directory: Not found")
    
    if LOG_DIR.exists():
        log_size = sum(f.stat().st_size for f in LOG_DIR.rglob("*.log") if f.is_file())
        log_count = len(list(LOG_DIR.rglob("*.log")))
        print(f"  Log directory: {format_size(log_size)} ({log_count} files)")
    else:
        print(f"  Log directory: Not found")
    print()
    
    # Health Summary
    print("🏥 Health Summary")
    print("-" * 80)
    
    health_issues = []
    
    if not config:
        health_issues.append("Configuration file missing")
    elif config.get("email", {}).get("sender_email") == "your-email@gmail.com":
        health_issues.append("Email not configured")
    
    if not latest:
        health_issues.append("No newsletter generated yet")
    elif latest and (datetime.now() - latest["modified"]) > timedelta(days=14):
        health_issues.append("Newsletter is outdated (>14 days old)")
    
    log_file = get_current_month_log()
    if log_file.exists():
        stats = parse_log_stats(log_file)
        if stats.get("errors", 0) > 5:
            health_issues.append(f"Multiple errors in logs ({stats['errors']})")
    
    if health_issues:
        print("⚠️  Issues detected:")
        for issue in health_issues:
            print(f"  - {issue}")
    else:
        print("✓ All systems operational")
    
    print()
    print("=" * 80)
    print("Last updated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)


def show_recent_logs(lines: int = 20) -> None:
    """Show recent log entries."""
    log_file = get_current_month_log()
    
    if not log_file.exists():
        print(f"No log file found: {log_file}")
        return
    
    print("=" * 80)
    print(f"📋 Recent Log Entries (Last {lines} lines)")
    print("=" * 80)
    
    with log_file.open("r", encoding="utf-8") as f:
        all_lines = f.readlines()
        recent = all_lines[-lines:]
        
        for line in recent:
            # Color code by log level
            if "ERROR" in line:
                print(f"\033[91m{line.rstrip()}\033[0m")  # Red
            elif "WARNING" in line:
                print(f"\033[93m{line.rstrip()}\033[0m")  # Yellow
            elif "✓" in line:
                print(f"\033[92m{line.rstrip()}\033[0m")  # Green
            else:
                print(line.rstrip())
    
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitoring Dashboard for arXiv Newsletter Automation"
    )
    parser.add_argument(
        "--logs",
        type=int,
        metavar="N",
        help="Show last N log entries instead of dashboard",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Refresh dashboard every 5 seconds (Ctrl+C to stop)",
    )
    
    args = parser.parse_args()
    
    if args.logs:
        show_recent_logs(args.logs)
    elif args.watch:
        try:
            import os
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                print_dashboard()
                print("\nRefreshing every 5 seconds... (Press Ctrl+C to stop)")
                import time
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n\nStopped.")
    else:
        print_dashboard()


if __name__ == "__main__":
    main()
