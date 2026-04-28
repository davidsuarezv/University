from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from P3_arxiv_analyze import analyze_papers
from P2_arxiv_process import filter_papers, normalize_papers
from P1_arxiv_search import fetch_arxiv_papers


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_MODEL = "llama3.2"
DEFAULT_BATCH_SIZE = 3
DEFAULT_MAX_RESULTS = 10
DEFAULT_TOP_N = 6
OLLAMA_API_URL = "http://localhost:11434/api/generate"


SYSTEM_PROMPT = """
You are an AI research analyst.
You analyze arXiv papers and produce grounded, readable summaries.
Only use the information provided in the paper metadata and abstracts.
Do not invent experiment results, datasets, or claims that are not supported by the input.
Return valid JSON only.
""".strip()


JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "paper_analyses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paper_index": {"type": "integer"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "main_contribution": {"type": "string"},
                    "methods": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "possible_use_cases": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "limitations_or_unknowns": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "novelty_score": {"type": "integer"},
                    "practicality_score": {"type": "integer"},
                    "why_it_matters": {"type": "string"},
                },
                "required": [
                    "paper_index",
                    "title",
                    "summary",
                    "main_contribution",
                    "methods",
                    "possible_use_cases",
                    "limitations_or_unknowns",
                    "novelty_score",
                    "practicality_score",
                    "why_it_matters",
                ],
                "additionalProperties": False,
            },
        },
        "batch_insight": {"type": "string"},
        "emerging_themes": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["paper_analyses", "batch_insight", "emerging_themes"],
    "additionalProperties": False,
}


FINAL_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "key_trends": {
            "type": "array",
            "items": {"type": "string"},
        },
        "most_promising_papers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "common_limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_next_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "executive_summary",
        "key_trends",
        "most_promising_papers",
        "common_limitations",
        "recommended_next_steps",
    ],
    "additionalProperties": False,
}


def slugify(value: str) -> str:
    safe = value.lower().strip()
    out = []
    previous_underscore = False

    for char in safe:
        if char.isalnum():
            out.append(char)
            previous_underscore = False
        else:
            if not previous_underscore:
                out.append("_")
                previous_underscore = True

    slug = "".join(out).strip("_")
    return slug or "query"


def build_paper_payload(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for idx, paper in enumerate(papers, start=1):
        payload.append(
            {
                "paper_index": idx,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "published_date": paper.get("published_date"),
                "categories": paper.get("categories", []),
                "ai_subdomain": paper.get("ai_subdomain"),
                "relevance_score": paper.get("relevance_score"),
                "relevance_label": paper.get("relevance_label"),
                "short_summary": paper.get("short_summary"),
                "abstract": paper.get("abstract", ""),
                "abs_url": paper.get("abs_url"),
                "pdf_url": paper.get("pdf_url"),
            }
        )
    return payload


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def extract_json_from_response(response_text: str) -> dict[str, Any]:
    """Extract JSON from Ollama's response, handling potential markdown code blocks."""
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Try to find JSON object in the text
    json_start = text.find('{')
    json_end = text.rfind('}')
    
    if json_start != -1 and json_end != -1:
        text = text[json_start:json_end + 1]
    
    return json.loads(text)


def call_ollama(
    prompt: str,
    model: str,
    system_prompt: str | None = None,
) -> str:
    """Call Ollama API and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",  # Tell Ollama to output JSON
    }
    
    if system_prompt:
        payload["system"] = system_prompt
    
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=300,  # 5 minutes timeout for longer responses
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
    
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to Ollama.")
        print("Make sure Ollama is running. Try: ollama serve")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\nError: Request timed out. The model might be taking too long.")
        print("Try using a smaller model or reducing batch size.")
        sys.exit(1)


def analyze_batch_with_ollama(
    papers: list[dict[str, Any]],
    user_query: str,
    model: str,
) -> dict[str, Any]:
    payload = build_paper_payload(papers)

    prompt = (
        f"Analyze these {len(papers)} arXiv papers about: {user_query}\n\n"
        f"PAPERS:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
        "Provide your analysis as a JSON object with:\n"
        '- "paper_analyses": array of objects, one per paper with:\n'
        '  - "paper_index": number\n'
        '  - "title": the paper title\n'
        '  - "summary": 2-3 sentence summary of what the paper does\n'
        '  - "main_contribution": what\'s new or important\n'
        '  - "methods": array of 2-3 key methods/techniques used\n'
        '  - "possible_use_cases": array of 2-3 practical applications\n'
        '  - "limitations_or_unknowns": array of 1-2 limitations\n'
        '  - "novelty_score": integer 1-10 (how novel/original)\n'
        '  - "practicality_score": integer 1-10 (how practical/useful)\n'
        '  - "why_it_matters": one sentence on importance\n'
        '- "batch_insight": one sentence summarizing the batch\n'
        '- "emerging_themes": array of 2-3 common themes across papers\n\n'
        "Respond with ONLY the JSON object, nothing else. Begin with {"
    )

    print("   Calling Ollama (this may take 30-60 seconds)...")
    response_text = call_ollama(prompt, model, system_prompt=SYSTEM_PROMPT)
    
    try:
        return extract_json_from_response(response_text)
    except json.JSONDecodeError as e:
        print(f"\nError parsing JSON from Ollama response: {e}")
        print("Response was:")
        print(response_text[:500])
        print("\nTrying to extract JSON more aggressively...")
        
        # Last resort: try to find any valid JSON in the response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # If all else fails, return a minimal valid response
        return {
            "paper_analyses": [
                {
                    "paper_index": i + 1,
                    "title": paper.get("title", ""),
                    "summary": "Analysis failed - could not parse model response",
                    "main_contribution": "Unknown",
                    "methods": ["Unable to determine"],
                    "possible_use_cases": ["Unable to determine"],
                    "limitations_or_unknowns": ["Analysis failed"],
                    "novelty_score": 5,
                    "practicality_score": 5,
                    "why_it_matters": "Unable to determine",
                }
                for i, paper in enumerate(papers)
            ],
            "batch_insight": "Analysis incomplete due to parsing error",
            "emerging_themes": ["Error in analysis"],
        }


def synthesize_final_report(
    all_batch_results: list[dict[str, Any]],
    user_query: str,
    model: str,
) -> dict[str, Any]:
    prompt = (
        f"Create a research briefing for: {user_query}\n\n"
        f"Based on these paper analyses:\n{json.dumps(all_batch_results, indent=2, ensure_ascii=False)}\n\n"
        "Provide a JSON object with:\n"
        '- "executive_summary": 3-4 sentence overview of findings\n'
        '- "key_trends": array of 3-5 major trends across the papers\n'
        '- "most_promising_papers": array of 2-3 paper titles that stand out\n'
        '- "common_limitations": array of 2-3 limitations seen across papers\n'
        '- "recommended_next_steps": array of 2-3 actionable next steps\n\n'
        "Respond with ONLY the JSON object. Begin with {"
    )

    print("   Calling Ollama for final synthesis (this may take 30-60 seconds)...")
    response_text = call_ollama(prompt, model, system_prompt=SYSTEM_PROMPT)
    
    try:
        return extract_json_from_response(response_text)
    except json.JSONDecodeError:
        # Return minimal valid response on error
        return {
            "executive_summary": "Unable to generate summary due to parsing error",
            "key_trends": ["Analysis incomplete"],
            "most_promising_papers": ["Unable to determine"],
            "common_limitations": ["Analysis failed"],
            "recommended_next_steps": ["Retry analysis"],
        }


def render_markdown_report(
    query: str,
    analyzed_papers: list[dict[str, Any]],
    batch_results: list[dict[str, Any]],
    final_report: dict[str, Any],
) -> str:
    lines: list[str] = []

    lines.append(f"# arXiv Research Report: {query}")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total papers analyzed**: {len(analyzed_papers)}")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append(final_report.get("executive_summary", "No summary available."))
    lines.append("")

    lines.append("## Key Trends")
    for item in final_report.get("key_trends", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Recommended Next Steps")
    for item in final_report.get("recommended_next_steps", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Detailed Paper Analysis")
    lines.append("")

    for i, paper in enumerate(analyzed_papers, start=1):
        lines.append(f"### {i}. {paper.get('title', 'Untitled')}")
        lines.append(f"- Relevance: {paper.get('relevance_score', 0):.0f}/100 ({paper.get('relevance_label', 'N/A')})")
        lines.append(f"- Subdomain: {paper.get('ai_subdomain', 'N/A')}")
        lines.append(f"- Published: {paper.get('published_date') or paper.get('published') or 'N/A'}")
        lines.append(f"- Categories: {', '.join(paper.get('categories', [])) or 'N/A'}")
        lines.append(f"- Abstract URL: {paper.get('abs_url') or 'N/A'}")
        lines.append(f"- PDF URL: {paper.get('pdf_url') or 'N/A'}")
        lines.append(f"- Local summary: {paper.get('short_summary', '')}")

        matched_analysis: dict[str, Any] | None = None
        for batch in batch_results:
            for item in batch.get("paper_analyses", []):
                if item.get("title") == paper.get("title"):
                    matched_analysis = item
                    break
            if matched_analysis:
                break

        if matched_analysis:
            lines.append(f"- AI summary: {matched_analysis.get('summary', '')}")
            lines.append(f"- Main contribution: {matched_analysis.get('main_contribution', '')}")
            lines.append(f"- Why it matters: {matched_analysis.get('why_it_matters', '')}")
            lines.append(f"- Novelty score: {matched_analysis.get('novelty_score', 0)}/10")
            lines.append(f"- Practicality score: {matched_analysis.get('practicality_score', 0)}/10")

            methods = matched_analysis.get("methods", [])
            if methods:
                lines.append("- Methods:")
                for method in methods:
                    lines.append(f"  - {method}")

            use_cases = matched_analysis.get("possible_use_cases", [])
            if use_cases:
                lines.append("- Possible use cases:")
                for use_case in use_cases:
                    lines.append(f"  - {use_case}")

            limitations = matched_analysis.get("limitations_or_unknowns", [])
            if limitations:
                lines.append("- Limitations / unknowns:")
                for limitation in limitations:
                    lines.append(f"  - {limitation}")

        lines.append("")

    lines.append("## Common Limitations")
    for item in final_report.get("common_limitations", []):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Most Promising Papers")
    for item in final_report.get("most_promising_papers", []):
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines)


def save_outputs(
    query: str,
    analyzed_papers: list[dict[str, Any]],
    batch_results: list[dict[str, Any]],
    final_report: dict[str, Any],
) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_slug = slugify(query)

    json_path = OUTPUT_DIR / f"arxiv_agent_report_{query_slug}_{timestamp}.json"
    md_path = OUTPUT_DIR / f"arxiv_agent_report_{query_slug}_{timestamp}.md"
    latest_json_path = OUTPUT_DIR / "arxiv_agent_report_latest.json"
    latest_md_path = OUTPUT_DIR / "arxiv_agent_report_latest.md"

    payload = {
        "query": query,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "papers": analyzed_papers,
        "batch_results": batch_results,
        "final_report": final_report,
    }

    markdown = render_markdown_report(query, analyzed_papers, batch_results, final_report)

    for path in [json_path, latest_json_path]:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    for path in [md_path, latest_md_path]:
        with path.open("w", encoding="utf-8") as f:
            f.write(markdown)

    return {
        "json": json_path,
        "markdown": md_path,
        "latest_json": latest_json_path,
        "latest_markdown": latest_md_path,
    }


def print_console_report(
    analyzed_papers: list[dict[str, Any]],
    final_report: dict[str, Any],
    saved_paths: dict[str, Path],
) -> None:
    print("\nFinal insight summary")
    print("=" * 100)
    print(final_report.get("executive_summary", "No summary available."))
    print()

    print("Top papers:")
    for i, paper in enumerate(analyzed_papers[:5], start=1):
        print(f"{i}. {paper.get('title', 'Untitled')}")
        print(
            f"   Relevance: {paper.get('relevance_score', 0):.0f}/100 | "
            f"Subdomain: {paper.get('ai_subdomain', 'N/A')}"
        )
        print(f"   Summary  : {paper.get('short_summary', '')}")
        print()

    print("Saved files:")
    print(f"- {saved_paths['json']}")
    print(f"- {saved_paths['markdown']}")
    print(f"- {saved_paths['latest_json']}")
    print(f"- {saved_paths['latest_markdown']}")


def check_ollama_available(model: str) -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        # Check if Ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        
        # Check if the specific model is available
        models = response.json().get("models", [])
        model_names = [m.get("name", "").split(":")[0] for m in models]
        
        if model not in model_names:
            print(f"\nWarning: Model '{model}' not found in Ollama.")
            print("Available models:", ", ".join(model_names) if model_names else "None")
            print(f"\nTo download the model, run: ollama pull {model}")
            return False
        
        return True
    
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to Ollama.")
        print("Make sure Ollama is running. Try: ollama serve")
        print("Or download from: https://ollama.com/download")
        return False
    except Exception as e:
        print(f"\nError checking Ollama: {e}")
        return False


def main() -> None:
    if len(sys.argv) < 2:
        print(
            'Usage: uv run python arxiv_agent_ollama.py "search terms" [max_results] [top_n] [batch_size] [model] [category] [keyword] [start_date] [end_date]'
        )
        sys.exit(1)

    search_terms = sys.argv[1]

    try:
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MAX_RESULTS
        top_n = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_TOP_N
        batch_size = int(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_BATCH_SIZE
    except ValueError:
        print("max_results, top_n, and batch_size must be integers.")
        sys.exit(1)

    model = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "none" else DEFAULT_MODEL
    category = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "none" else None
    keyword = sys.argv[7] if len(sys.argv) > 7 and sys.argv[7] != "none" else None
    start_date = sys.argv[8] if len(sys.argv) > 8 and sys.argv[8] != "none" else None
    end_date = sys.argv[9] if len(sys.argv) > 9 and sys.argv[9] != "none" else None

    if top_n > max_results:
        top_n = max_results

    # Check if Ollama is available
    if not check_ollama_available(model):
        sys.exit(1)

    print(f"Running Ollama-enhanced analysis for query: {search_terms}")
    print(f"Model      : {model}")
    print(f"Max results: {max_results}")
    print(f"Top N      : {top_n}")
    print(f"Batch size : {batch_size}")
    print(f"Output dir : {OUTPUT_DIR}")
    print("\nNote: Ollama responses may take 30-60 seconds per batch.")

    try:
        raw_papers = fetch_arxiv_papers(
            search_terms=search_terms,
            start=0,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )

        processed_papers = normalize_papers(raw_papers)
        filtered_papers = filter_papers(
            processed_papers,
            category=category,
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
        )

        analyzed_papers = analyze_papers(filtered_papers, user_query=search_terms)
        analyzed_papers = analyzed_papers[:top_n]

        if not analyzed_papers:
            print("No papers found after filtering.")
            sys.exit(0)

        batches = chunked(analyzed_papers, batch_size)
        batch_results: list[dict[str, Any]] = []

        for i, batch in enumerate(batches, start=1):
            print(f"\nAnalyzing batch {i}/{len(batches)} with {len(batch)} paper(s)...")
            batch_result = analyze_batch_with_ollama(
                papers=batch,
                user_query=search_terms,
                model=model,
            )
            batch_results.append(batch_result)
            time.sleep(1)  # Small delay between batches

        print("\nSynthesizing final report...")
        final_report = synthesize_final_report(
            all_batch_results=batch_results,
            user_query=search_terms,
            model=model,
        )

        saved_paths = save_outputs(
            query=search_terms,
            analyzed_papers=analyzed_papers,
            batch_results=batch_results,
            final_report=final_report,
        )

        print_console_report(analyzed_papers, final_report, saved_paths)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(0)
    except Exception as exc:
        print(f"\nError: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()