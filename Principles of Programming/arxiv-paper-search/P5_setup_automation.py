#!/usr/bin/env python3
"""
Quick Setup Script for arXiv Newsletter Automation

This interactive script helps you set up the automation system
by walking through configuration step-by-step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "automation_config.json"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def get_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    return input(f"{prompt}: ").strip()


def get_yes_no(prompt: str, default: bool = True) -> bool:
    """Get yes/no input from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ["y", "yes"]:
            return True
        if response in ["n", "no"]:
            return False
        print("Please enter 'y' or 'n'")


def get_email_config() -> dict[str, Any]:
    """Configure email settings."""
    print_header("📧 Email Configuration")
    
    print("\nFor Gmail users:")
    print("  1. Enable 2-factor authentication")
    print("  2. Create an App Password: https://myaccount.google.com/apppasswords")
    print("  3. Use the 16-character app password below")
    print("\nFor other providers, use your SMTP settings.")
    
    sender_email = get_input("\nSender email address")
    while not "@" in sender_email:
        print("Invalid email address")
        sender_email = get_input("Sender email address")
    
    sender_password = get_input("Sender password/app password")
    
    # Determine SMTP server based on email
    if "gmail.com" in sender_email:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        print(f"\n✓ Using Gmail SMTP: {smtp_server}:{smtp_port}")
    elif "outlook.com" in sender_email or "hotmail.com" in sender_email:
        smtp_server = "smtp-mail.outlook.com"
        smtp_port = 587
        print(f"\n✓ Using Outlook SMTP: {smtp_server}:{smtp_port}")
    elif "yahoo.com" in sender_email:
        smtp_server = "smtp.mail.yahoo.com"
        smtp_port = 587
        print(f"\n✓ Using Yahoo SMTP: {smtp_server}:{smtp_port}")
    else:
        smtp_server = get_input("SMTP server", "smtp.gmail.com")
        smtp_port = int(get_input("SMTP port", "587"))
    
    # Recipients
    print("\nEnter recipient email addresses (one per line, empty line to finish):")
    recipients = []
    while True:
        recipient = get_input("Recipient email")
        if not recipient:
            break
        if "@" in recipient:
            recipients.append(recipient)
        else:
            print("Invalid email, skipped")
    
    if not recipients:
        recipients = [sender_email]  # Send to self by default
        print(f"No recipients entered, using sender email: {sender_email}")
    
    subject_prefix = get_input("Email subject prefix", "[AI Research Weekly]")
    
    return {
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "sender_email": sender_email,
        "sender_password": sender_password,
        "recipients": recipients,
        "subject_prefix": subject_prefix,
    }


def get_search_config() -> dict[str, Any]:
    """Configure search settings."""
    print_header("🔍 Search Configuration")
    
    print("\nDefault AI research topics:")
    default_queries = [
        "large language models",
        "transformer architectures",
        "reinforcement learning",
    ]
    
    print("Current topics:")
    for i, query in enumerate(default_queries, 1):
        print(f"  {i}. {query}")
    
    if get_yes_no("\nWould you like to customize the topics?", False):
        queries = []
        print("\nEnter search topics (one per line, empty line to finish):")
        while True:
            query = get_input(f"Topic {len(queries) + 1}")
            if not query:
                break
            queries.append(query)
        
        if queries:
            default_queries = queries
    
    max_results = int(get_input("\nMax papers to fetch per topic", "15"))
    top_n = int(get_input("Top papers to analyze per topic", "10"))
    batch_size = int(get_input("Batch size for Ollama analysis", "3"))
    
    print("\nAvailable Ollama models:")
    print("  - llama3.2 (recommended, fast)")
    print("  - mistral (alternative)")
    print("  - llama2 (older)")
    print("  Run 'ollama list' to see installed models")
    
    model = get_input("Ollama model to use", "llama3.2")
    
    return {
        "default_queries": default_queries,
        "max_results_per_query": max_results,
        "top_n_papers": top_n,
        "batch_size": batch_size,
        "ollama_model": model,
    }


def get_schedule_config() -> dict[str, Any]:
    """Configure schedule settings."""
    print_header("📅 Schedule Configuration")
    
    print("\nDays of week:")
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days, 1):
        print(f"  {i}. {day.capitalize()}")
    
    day_num = int(get_input("Select day (1-7)", "1"))
    day_of_week = days[day_num - 1] if 1 <= day_num <= 7 else "monday"
    
    time = get_input("Time to run (HH:MM in 24-hour format)", "09:00")
    
    # Validate time format
    try:
        hours, minutes = map(int, time.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
    except:
        print("Invalid time format, using default 09:00")
        time = "09:00"
    
    print(f"\n✓ Newsletter will run every {day_of_week.capitalize()} at {time}")
    
    return {
        "day_of_week": day_of_week,
        "time": time,
        "timezone": "UTC",
    }


def get_newsletter_config() -> dict[str, Any]:
    """Configure newsletter settings."""
    print_header("📰 Newsletter Configuration")
    
    newsletter_name = get_input("\nNewsletter name", "AI Research Insights")
    max_papers = int(get_input("Max papers in newsletter", "8"))
    
    include_snippets = get_yes_no("Include abstract snippets?", True)
    include_breakdown = get_yes_no("Include subdomain breakdown?", True)
    
    return {
        "newsletter_name": newsletter_name,
        "include_abstract_snippets": include_snippets,
        "max_papers_in_newsletter": max_papers,
        "include_subdomain_breakdown": include_breakdown,
    }


def get_monitoring_config() -> dict[str, Any]:
    """Configure monitoring settings."""
    print_header("📊 Monitoring Configuration")
    
    enable_logging = get_yes_no("\nEnable logging?", True)
    
    log_retention = int(get_input("Log retention (days)", "30"))
    
    send_errors = get_yes_no("Send error notifications?", True)
    
    return {
        "enable_logging": enable_logging,
        "log_retention_days": log_retention,
        "send_error_notifications": send_errors,
    }


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    with CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Configuration saved to: {CONFIG_FILE}")


def test_email_connection(config: dict[str, Any]) -> bool:
    """Test email connection."""
    print_header("🧪 Testing Email Connection")
    
    email_config = config["email"]
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        print("\nConnecting to SMTP server...")
        with smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"]) as server:
            server.starttls()
            print("✓ TLS connection established")
            
            print("Authenticating...")
            server.login(email_config["sender_email"], email_config["sender_password"])
            print("✓ Authentication successful")
            
            if get_yes_no("\nSend a test email?", False):
                msg = MIMEMultipart()
                msg["Subject"] = "Test Email from arXiv Newsletter Automation"
                msg["From"] = email_config["sender_email"]
                msg["To"] = email_config["sender_email"]
                
                body = "This is a test email from the arXiv Newsletter Automation setup.\n\nIf you received this, your email configuration is working correctly!"
                msg.attach(MIMEText(body, "plain"))
                
                server.send_message(msg)
                print(f"✓ Test email sent to {email_config['sender_email']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Email test failed: {e}")
        print("\nPlease check your email settings and try again.")
        return False


def check_ollama() -> bool:
    """Check if Ollama is installed and running."""
    print_header("🤖 Checking Ollama")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        
        models = response.json().get("models", [])
        model_names = [m.get("name", "").split(":")[0] for m in models]
        
        print("\n✓ Ollama is running")
        print(f"✓ Installed models: {', '.join(model_names) if model_names else 'None'}")
        
        if not model_names:
            print("\nNo models found. Run: ollama pull llama3.2")
            return False
        
        return True
        
    except:
        print("\n✗ Ollama is not running or not installed")
        print("\nPlease install Ollama:")
        print("  - macOS: brew install ollama")
        print("  - Or download from: https://ollama.com/download")
        print("\nThen start it: ollama serve")
        print("And pull a model: ollama pull llama3.2")
        return False


def main() -> None:
    """Main setup flow."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     arXiv Research Newsletter Automation - Quick Setup              ║
║                                                                      ║
║     This wizard will help you configure the automation system       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Check if config already exists
    if CONFIG_FILE.exists():
        if not get_yes_no("\nConfiguration file already exists. Overwrite?", False):
            print("Setup cancelled.")
            return
    
    # Check Ollama
    ollama_ok = check_ollama()
    if not ollama_ok:
        if not get_yes_no("\nContinue setup anyway?", True):
            print("Setup cancelled.")
            return
    
    # Gather all configuration
    config = {
        "email": get_email_config(),
        "search": get_search_config(),
        "schedule": get_schedule_config(),
        "newsletter": get_newsletter_config(),
        "monitoring": get_monitoring_config(),
    }
    
    # Save configuration
    save_config(config)
    
    # Test email (optional)
    if get_yes_no("\nTest email configuration?", True):
        test_email_connection(config)
    
    # Final instructions
    print_header("✅ Setup Complete!")
    
    print("""
Next steps:

1. Test the system:
   python arxiv_automation.py --run-now

2. Start the scheduler:
   python arxiv_automation.py --schedule

3. Monitor the system:
   python monitor_dashboard.py

4. View recent logs:
   python monitor_dashboard.py --logs 50

For more information, see AUTOMATION_README.md
""")
    
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
