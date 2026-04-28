# arXiv AI Research Newsletter Automation

An automated system that fetches AI research papers from arXiv, analyzes them using local LLM (Ollama), and delivers weekly newsletter summaries via email.

## Project Structure

```
arxiv-paper-search/
├── P1_arxiv_search.py              # Fetch papers from arXiv API
├── P2_arxiv_process.py             # Process and normalize paper data
├── P3_arxiv_analyze.py             # Analyze and rank papers using relevance scoring
├── P4_arxiv_agent_ollama.py        # Main pipeline orchestration
├── P5_arxiv_automation.py          # Newsletter generation and email delivery
├── P5_setup_automation.py          # Interactive configuration setup
├── P5_monitor_dashboard.py         # System monitoring dashboard
├── automation_config.json          # Configuration file (email, schedule, topics)
├── pyproject.toml                  # Project dependencies
├── requirements_automation.txt     # Additional automation dependencies
└── main.py                         # Entry point
```

**Module responsibilities:**
- **P1**: arXiv API search and retrieval
- **P2**: Data extraction and filtering  
- **P3**: LLM-powered relevance scoring and categorization
- **P4**: Complete analysis pipeline
- **P5_automation**: Scheduled newsletter generation and email sending
- **P5_setup**: Configuration wizard
- **P5_monitor**: Health monitoring and logs

## Required Dependencies

### System Requirements
- Python 3.14+
- Ollama (local LLM server) - Install from https://ollama.ai
- 8GB+ RAM

### Python Dependencies

From `pyproject.toml`:
```
feedparser>=6.0.12
requests>=2.33.1
anthropic>=0.96.0
openai>=2.32.0
pypdf>=6.10.2
```

From `requirements_automation.txt`:
```
schedule>=1.2.0
```

Built-in libraries (no installation needed): `smtplib`, `email`, `json`, `csv`

### Installation
```bash
# Install all dependencies
uv pip install -e .
uv pip install -r requirements_automation.txt
```

## How to Run the Code

### 1. Initial Setup

**Install Ollama and pull a model:**
```bash
# Install from https://ollama.ai, then:
ollama pull llama3.2
ollama list  # Verify installation
```

**Set up Python environment:**
```bash
# Create and activate virtual environment
uv venv
.venv\Scripts\activate              # Windows
source .venv/bin/activate           # macOS/Linux

# Install dependencies
uv pip install -e .
uv pip install -r requirements_automation.txt
```

**Configure the system (interactive):**
```bash
python P5_setup_automation.py
```
This wizard configures:
- Email settings (SMTP server, sender, recipients)
- Search topics (AI research areas)
- Schedule (day/time for newsletters)
- Newsletter preferences

### 2. Running the System

**Manual paper analysis:**
```bash
# Search arXiv
python P1_arxiv_search.py "transformer" 10

# Process papers
python P2_arxiv_process.py "large language models" 20

# Full analysis with ranking
python P3_arxiv_analyze.py "multimodal reasoning" 15

# Complete pipeline
python P4_arxiv_agent_ollama.py
```

**Automated newsletter:**
```bash
# Generate and send newsletter now
python P5_arxiv_automation.py --run-now

# Start weekly scheduled automation
python P5_arxiv_automation.py --schedule

# Test email configuration
python P5_arxiv_automation.py --test-email
```

**Monitoring:**
```bash
# View system dashboard
python P5_monitor_dashboard.py

# View recent logs
python P5_monitor_dashboard.py --logs 50
```

### 3. Configuration

Edit `automation_config.json` to customize:
```json
{
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipients": ["recipient@example.com"]
  },
  "search": {
    "default_queries": ["large language models", "transformer"],
    "ollama_model": "llama3.2"
  },
  "schedule": {
    "day_of_week": "monday",
    "time": "08:00"
  }
}
```

**Gmail users:** Enable 2FA and create an App Password at https://myaccount.google.com/apppasswords

---

**Note:** This system uses Ollama for free local LLM inference, avoiding paid API costs.
