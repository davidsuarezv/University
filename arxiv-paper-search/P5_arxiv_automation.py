"""
arXiv Research Automation & Newsletter System

This script automates weekly arXiv research analysis and sends HTML newsletters
containing AI research insights to a configured list of recipients.

Features:
- Automated weekly scheduling
- HTML email newsletter generation
- Configurable recipient lists
- Monitoring and logging
- Error handling and retry logic
"""

from __future__ import annotations

import json
import logging
import smtplib
import sys
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import schedule

import os
from dotenv import load_dotenv
load_dotenv()

# Import your existing modules
try:
    from P4_arxiv_agent_ollama import (
        analyze_papers,
        analyze_batch_with_ollama,
        chunked,
        synthesize_final_report,
        check_ollama_available,
    )
    from P2_arxiv_process import filter_papers, normalize_papers
    from P1_arxiv_search import fetch_arxiv_papers
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure P1_arxiv_search.py, P2_arxiv_process.py, and P4_arxiv_agent_ollama.py are in the same directory.")
    sys.exit(1)


# Configuration
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output newsletter"
LOG_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "automation_config.json"

# Create necessary directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOG_DIR / f"automation_{datetime.now().strftime('%Y%m')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class NewsletterConfig:
    """Configuration for the newsletter system."""

    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self.config = self.load_config()
    def load_config(self) -> dict[str, Any]:
        """Load configuration from JSON file or create default."""
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = self.get_default_config()
            self.save_config(config)

        # Override email secrets with values from .env (never stored in git)
        env_email = os.getenv("SENDER_EMAIL")
        env_password = os.getenv("SENDER_PASSWORD")
        env_recipient = os.getenv("RECIPIENT_EMAIL")

        if env_email:
            config["email"]["sender_email"] = env_email
        if env_password:
            config["email"]["sender_password"] = env_password
        if env_recipient:
            config["email"]["recipients"] = [env_recipient]

        return config

    def get_default_config(self) -> dict[str, Any]:
        """Return default configuration."""
        return {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "your-email@gmail.com",
                "sender_password": "your-app-password",
                "recipients": [
                    "recipient1@example.com",
                    "recipient2@example.com",
                ],
                "subject_prefix": "[AI Research Weekly]",
            },
            "search": {
                "default_queries": [
                    "large language models",
                    "transformer architectures",
                    "reinforcement learning",
                ],
                "max_results_per_query": 15,
                "top_n_papers": 10,
                "batch_size": 3,
                "ollama_model": "llama3.2",
            },
            "schedule": {
                "day_of_week": "monday",
                "time": "13:42",
                "timezone": "UTC",
            },
            "newsletter": {
                "newsletter_name": "AI Research Insights",
                "include_abstract_snippets": True,
                "max_papers_in_newsletter": 8,
                "include_subdomain_breakdown": True,
            },
            "monitoring": {
                "enable_logging": True,
                "log_retention_days": 30,
                "send_error_notifications": True,
            },
        }

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to JSON file."""
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to {self.config_path}")

    def update_config(self, updates: dict[str, Any]) -> None:
        """Update configuration with new values."""
        self.config.update(updates)
        self.save_config(self.config)


def generate_html_newsletter(
    analyzed_papers: list[dict[str, Any]],
    final_report: dict[str, Any],
    query: str,
    config: NewsletterConfig,
) -> str:
    """
    Generate an HTML newsletter from analyzed papers and AI insights.
    
    Args:
        analyzed_papers: List of analyzed papers with relevance scores
        final_report: Final synthesis report from Ollama
        query: Original search query
        config: Newsletter configuration
        
    Returns:
        HTML string for the email newsletter
    """
    newsletter_config = config.config["newsletter"]
    max_papers = newsletter_config["max_papers_in_newsletter"]
    newsletter_name = newsletter_config["newsletter_name"]
    
    # Get current date range (past week)
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    date_range = f"{week_ago.strftime('%B %d')} - {today.strftime('%B %d, %Y')}"
    
    # Start building HTML
    html_parts = [
        """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{newsletter_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #4A90E2;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #2C3E50;
            margin: 0;
            font-size: 28px;
        }}
        .subtitle {{
            color: #7F8C8D;
            margin-top: 5px;
            font-size: 14px;
        }}
        .executive-summary {{
            background-color: #EBF5FF;
            border-left: 4px solid #4A90E2;
            padding: 20px;
            margin: 30px 0;
            border-radius: 4px;
        }}
        .executive-summary h2 {{
            margin-top: 0;
            color: #2C3E50;
            font-size: 20px;
        }}
        .key-trends {{
            background-color: #FFF9E6;
            border-left: 4px solid #F39C12;
            padding: 20px;
            margin: 30px 0;
            border-radius: 4px;
        }}
        .key-trends h2 {{
            margin-top: 0;
            color: #2C3E50;
            font-size: 20px;
        }}
        .key-trends ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .key-trends li {{
            margin: 8px 0;
        }}
        .paper {{
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
            background-color: #FAFAFA;
        }}
        .paper-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        .paper-title {{
            font-size: 18px;
            font-weight: 600;
            color: #2C3E50;
            margin: 0 0 10px 0;
            flex: 1;
        }}
        .relevance-badge {{
            background-color: #27AE60;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
            margin-left: 10px;
        }}
        .relevance-badge.high {{
            background-color: #27AE60;
        }}
        .relevance-badge.medium {{
            background-color: #F39C12;
        }}
        .relevance-badge.low {{
            background-color: #95A5A6;
        }}
        .paper-meta {{
            color: #7F8C8D;
            font-size: 13px;
            margin-bottom: 10px;
        }}
        .paper-meta span {{
            margin-right: 15px;
        }}
        .subdomain-tag {{
            display: inline-block;
            background-color: #E8F4F8;
            color: #2980B9;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 500;
            margin-right: 5px;
        }}
        .paper-summary {{
            color: #555;
            margin: 15px 0;
            line-height: 1.7;
        }}
        .paper-links {{
            margin-top: 15px;
        }}
        .paper-links a {{
            color: #4A90E2;
            text-decoration: none;
            margin-right: 15px;
            font-weight: 500;
            font-size: 14px;
        }}
        .paper-links a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #E0E0E0;
            text-align: center;
            color: #7F8C8D;
            font-size: 12px;
        }}
        .stats-box {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            padding: 20px;
            background-color: #F8F9FA;
            border-radius: 6px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-number {{
            font-size: 32px;
            font-weight: 700;
            color: #4A90E2;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 13px;
            color: #7F8C8D;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {newsletter_name}</h1>
            <div class="subtitle">{date_range}</div>
        </div>
""".format(
            newsletter_name=newsletter_name,
            date_range=date_range,
        )
    ]

    # Statistics box
    subdomain_counts: dict[str, int] = {}
    for paper in analyzed_papers:
        subdomain = paper.get("ai_subdomain", "General AI")
        subdomain_counts[subdomain] = subdomain_counts.get(subdomain, 0) + 1

    html_parts.append(
        f"""
        <div class="stats-box">
            <div class="stat">
                <div class="stat-number">{len(analyzed_papers)}</div>
                <div class="stat-label">Papers Analyzed</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len(subdomain_counts)}</div>
                <div class="stat-label">AI Subdomains</div>
            </div>
            <div class="stat">
                <div class="stat-number">{max_papers}</div>
                <div class="stat-label">Featured Papers</div>
            </div>
        </div>
"""
    )

    # Executive Summary
    executive_summary = final_report.get("executive_summary", "")
    if executive_summary:
        html_parts.append(
            f"""
        <div class="executive-summary">
            <h2>📊 Executive Summary</h2>
            <p>{executive_summary}</p>
        </div>
"""
        )

    # Key Trends
    key_trends = final_report.get("key_trends", [])
    if key_trends:
        trends_html = "<ul>"
        for trend in key_trends:
            trends_html += f"<li>{trend}</li>"
        trends_html += "</ul>"
        
        html_parts.append(
            f"""
        <div class="key-trends">
            <h2>🔥 Key Trends This Week</h2>
            {trends_html}
        </div>
"""
        )

    # Featured Papers Section
    html_parts.append(
        """
        <h2 style="color: #2C3E50; margin-top: 40px; margin-bottom: 20px;">
            📚 Featured Research Papers
        </h2>
"""
    )

    # Add papers
    for i, paper in enumerate(analyzed_papers[:max_papers], start=1):
        title = paper.get("title", "Untitled")
        authors = paper.get("authors", [])
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        
        published_date = paper.get("published_date", "N/A")
        subdomain = paper.get("ai_subdomain", "General AI")
        
        relevance_score = paper.get("relevance_score", 0)
        if relevance_score >= 80:
            badge_class = "high"
            badge_text = f"{relevance_score:.0f}/100 - Highly Relevant"
        elif relevance_score >= 50:
            badge_class = "medium"
            badge_text = f"{relevance_score:.0f}/100 - Relevant"
        else:
            badge_class = "low"
            badge_text = f"{relevance_score:.0f}/100"
        
        summary = paper.get("short_summary", "No summary available.")
        abs_url = paper.get("abs_url", "#")
        pdf_url = paper.get("pdf_url", "#")
        
        categories = ", ".join(paper.get("categories", []))
        
        html_parts.append(
            f"""
        <div class="paper">
            <div class="paper-header">
                <h3 class="paper-title">{i}. {title}</h3>
                <span class="relevance-badge {badge_class}">{badge_text}</span>
            </div>
            <div class="paper-meta">
                <span>👥 {author_str}</span>
                <span>📅 {published_date}</span>
            </div>
            <div class="paper-meta">
                <span class="subdomain-tag">{subdomain}</span>
                {f'<span style="color: #95A5A6; font-size: 11px;">{categories}</span>' if categories else ''}
            </div>
            <div class="paper-summary">
                {summary}
            </div>
            <div class="paper-links">
                <a href="{abs_url}" target="_blank">📄 Read Abstract</a>
                <a href="{pdf_url}" target="_blank">⬇️ Download PDF</a>
            </div>
        </div>
"""
        )

    # Subdomain breakdown (optional)
    if newsletter_config.get("include_subdomain_breakdown", True) and subdomain_counts:
        html_parts.append(
            """
        <div style="margin-top: 40px; padding: 20px; background-color: #F8F9FA; border-radius: 6px;">
            <h3 style="color: #2C3E50; margin-top: 0;">📈 Research by AI Subdomain</h3>
            <ul style="list-style: none; padding: 0;">
"""
        )
        
        for subdomain, count in sorted(subdomain_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(analyzed_papers)) * 100
            html_parts.append(
                f"""
                <li style="margin: 8px 0;">
                    <strong>{subdomain}</strong>: {count} paper{'s' if count != 1 else ''} ({percentage:.1f}%)
                </li>
"""
            )
        
        html_parts.append(
            """
            </ul>
        </div>
"""
        )

    # Footer
    html_parts.append(
        f"""
        <div class="footer">
            <p>Generated automatically by arXiv Research Automation System</p>
            <p>Analysis powered by Ollama • Data from arXiv.org</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>
    </div>
</body>
</html>
"""
    )

    return "".join(html_parts)


def send_email(
    recipients: list[str],
    subject: str,
    html_content: str,
    config: NewsletterConfig,
) -> bool:
    """
    Send HTML email to recipients.
    
    Args:
        recipients: List of email addresses
        subject: Email subject line
        html_content: HTML content of the email
        config: Newsletter configuration
        
    Returns:
        True if email sent successfully, False otherwise
    """
    email_config = config.config["email"]
    
    sender_email = email_config["sender_email"]
    sender_password = email_config["sender_password"]
    smtp_server = email_config["smtp_server"]
    smtp_port = email_config["smtp_port"]
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipients)
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication failed. Check your email and password.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def run_research_and_newsletter(config: NewsletterConfig) -> bool:
    """
    Execute the full research pipeline and send newsletter.
    
    Args:
        config: Newsletter configuration
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("=" * 80)
    logger.info("Starting automated research analysis and newsletter generation")
    logger.info("=" * 80)
    
    search_config = config.config["search"]
    email_config = config.config["email"]
    newsletter_config = config.config["newsletter"]
    
    queries = search_config["default_queries"]
    max_results_per_query = search_config["max_results_per_query"]
    top_n = search_config["top_n_papers"]
    batch_size = search_config["batch_size"]
    model = search_config["ollama_model"]
    
    # Check Ollama availability
    if not check_ollama_available(model):
        logger.error(f"Ollama model '{model}' is not available. Aborting.")
        return False
    
    all_analyzed_papers: list[dict[str, Any]] = []
    
    try:
        # Process each query
        for query_idx, query in enumerate(queries, start=1):
            logger.info(f"\n[{query_idx}/{len(queries)}] Processing query: '{query}'")
            
            # Fetch papers
            logger.info(f"Fetching up to {max_results_per_query} papers from arXiv...")
            raw_papers = fetch_arxiv_papers(
                search_terms=query,
                start=0,
                max_results=max_results_per_query,
                sort_by="submittedDate",
                sort_order="descending",
            )
            
            # Process and filter
            processed_papers = normalize_papers(raw_papers)
            
            # Analyze papers
            logger.info(f"Analyzing {len(processed_papers)} papers...")
            analyzed = analyze_papers(processed_papers, user_query=query)
            
            all_analyzed_papers.extend(analyzed[:top_n])
        
        # Remove duplicates based on title
        seen_titles: set[str] = set()
        unique_papers: list[dict[str, Any]] = []
        
        for paper in all_analyzed_papers:
            title = paper.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)
        
        # Sort by relevance score
        unique_papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
        
        # Limit to top papers
        final_papers = unique_papers[:newsletter_config["max_papers_in_newsletter"]]
        
        logger.info(f"\nTotal unique papers after deduplication: {len(unique_papers)}")
        logger.info(f"Selected top {len(final_papers)} papers for newsletter")
        
        if not final_papers:
            logger.warning("No papers found. Skipping newsletter generation.")
            return False
        
        # Generate AI insights with Ollama
        logger.info("\nGenerating AI insights with Ollama...")
        batches = chunked(final_papers, batch_size)
        batch_results: list[dict[str, Any]] = []
        
        for i, batch in enumerate(batches, start=1):
            logger.info(f"Analyzing batch {i}/{len(batches)} ({len(batch)} papers)...")
            batch_result = analyze_batch_with_ollama(
                papers=batch,
                user_query=" + ".join(queries),
                model=model,
            )
            batch_results.append(batch_result)
            time.sleep(1)
        
        logger.info("Synthesizing final report...")
        final_report = synthesize_final_report(
            all_batch_results=batch_results,
            user_query="AI Research Weekly Digest",
            model=model,
        )
        
        # Generate newsletter HTML
        logger.info("Generating HTML newsletter...")
        html_content = generate_html_newsletter(
            analyzed_papers=final_papers,
            final_report=final_report,
            query=" + ".join(queries),
            config=config,
        )
        
        # Save newsletter to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        newsletter_path = OUTPUT_DIR / f"newsletter_{timestamp}.html"
        with newsletter_path.open("w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Newsletter saved to: {newsletter_path}")
        
        # Also save as latest
        latest_path = OUTPUT_DIR / "newsletter_latest.html"
        with latest_path.open("w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Send email
        recipients = email_config["recipients"]
        subject_prefix = email_config["subject_prefix"]
        subject = f"{subject_prefix} {newsletter_config['newsletter_name']} - {datetime.now().strftime('%B %d, %Y')}"
        
        logger.info(f"Sending newsletter to {len(recipients)} recipient(s)...")
        success = send_email(recipients, subject, html_content, config)
        
        if success:
            logger.info("✓ Newsletter sent successfully!")
            return True
        else:
            logger.error("✗ Failed to send newsletter")
            return False
            
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Error in research pipeline: {e}", exc_info=True)
        return False


def schedule_weekly_run(config: NewsletterConfig) -> None:
    """
    Schedule the newsletter to run weekly.
    
    Args:
        config: Newsletter configuration
    """
    schedule_config = config.config["schedule"]
    day_of_week = schedule_config["day_of_week"]
    run_time = schedule_config["time"]
    
    # Map day names to schedule functions
    day_mapping = {
        "monday": schedule.every().monday,
        "tuesday": schedule.every().tuesday,
        "wednesday": schedule.every().wednesday,
        "thursday": schedule.every().thursday,
        "friday": schedule.every().friday,
        "saturday": schedule.every().saturday,
        "sunday": schedule.every().sunday,
    }
    
    scheduler = day_mapping.get(day_of_week.lower(), schedule.every().monday)
    scheduler.at(run_time).do(run_research_and_newsletter, config=config)
    
    logger.info(f"Scheduled weekly newsletter for {day_of_week.capitalize()} at {run_time}")


def cleanup_old_logs(retention_days: int = 30) -> None:
    """Remove log files older than retention_days."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for log_file in LOG_DIR.glob("automation_*.log"):
        try:
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff:
                log_file.unlink()
                logger.info(f"Removed old log file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not remove log file {log_file}: {e}")


def main() -> None:
    """Main entry point for the automation script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="arXiv Research Automation & Newsletter System"
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the newsletter generation immediately (don't schedule)",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Start the scheduler for weekly automated runs",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(CONFIG_FILE),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create a default configuration file and exit",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = NewsletterConfig(Path(args.config))
    
    if args.create_config:
        logger.info(f"Created default configuration at: {config.config_path}")
        logger.info("Please edit this file with your email settings and preferences.")
        return
    
    # Validate email configuration
    email_config = config.config["email"]
    if email_config["sender_email"] == "your-email@gmail.com":
        logger.error("Please configure your email settings in automation_config.json")
        logger.error("Run with --create-config to create a template configuration file")
        sys.exit(1)
    
    if args.run_now:
        # Run immediately
        logger.info("Running newsletter generation now...")
        success = run_research_and_newsletter(config)
        sys.exit(0 if success else 1)
    
    elif args.schedule:
        # Start scheduler
        logger.info("Starting automated scheduler...")
        schedule_weekly_run(config)
        
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        logger.info(f"Next run: {schedule.next_run()}")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
                # Cleanup old logs periodically
                if datetime.now().hour == 0 and datetime.now().minute < 5:
                    retention_days = config.config["monitoring"].get("log_retention_days", 30)
                    cleanup_old_logs(retention_days)
                    
        except KeyboardInterrupt:
            logger.info("\nScheduler stopped by user")
            sys.exit(0)
    
    else:
        parser.print_help()
        logger.info("\nQuick start:")
        logger.info("  1. Create config: python arxiv_automation.py --create-config")
        logger.info("  2. Edit automation_config.json with your settings")
        logger.info("  3. Test: python arxiv_automation.py --run-now")
        logger.info("  4. Schedule: python arxiv_automation.py --schedule")


if __name__ == "__main__":
    main()
