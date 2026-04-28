from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from P2_arxiv_process import filter_papers, normalize_papers
from P1_arxiv_search import fetch_arxiv_papers


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


AI_SUBDOMAIN_RULES: dict[str, dict[str, list[str]]] = {
    "NLP": {
        "categories": ["cs.CL"],
        "keywords": [
            "language model",
            "llm",
            "nlp",
            "natural language",
            "translation",
            "summarization",
            "question answering",
            "retrieval",
            "prompt",
            "token",
            "text generation",
            "instruction tuning",
        ],
    },
    "Computer Vision": {
        "categories": ["cs.CV"],
        "keywords": [
            "vision",
            "image",
            "video",
            "segmentation",
            "object detection",
            "diffusion",
            "visual recognition",
            "vision-language",
        ],
    },
    "Machine Learning": {
        "categories": ["cs.LG"],
        "keywords": [
            "machine learning",
            "representation learning",
            "supervised",
            "unsupervised",
            "optimization",
            "generalization",
            "classification",
            "regression",
        ],
    },
    "Reinforcement Learning": {
        "categories": ["cs.LG", "cs.AI"],
        "keywords": [
            "reinforcement learning",
            "policy",
            "reward",
            "agent",
            "markov decision process",
            "q-learning",
        ],
    },
    "Reasoning and Agents": {
        "categories": ["cs.AI"],
        "keywords": [
            "reasoning",
            "planning",
            "agent",
            "tool use",
            "multi-agent",
            "decision making",
        ],
    },
    "Multimodal AI": {
        "categories": ["cs.CL", "cs.CV", "cs.AI"],
        "keywords": [
            "multimodal",
            "vision-language",
            "audio-text",
            "cross-modal",
            "image-text",
            "video-language",
        ],
    },
}


GENERIC_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "we",
    "with", "using", "use", "used", "via", "our", "these", "those", "can", "may",
    "new", "paper", "study", "results", "show", "shows", "based", "method",
    "methods", "model", "models", "approach", "approaches"
}


def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{1,}", text.lower())
    return [word for word in words if word not in GENERIC_STOPWORDS]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "query"


def summarize_abstract(abstract: str, max_sentences: int = 2) -> str:
    if not abstract.strip():
        return "No abstract available."

    sentences = re.split(r"(?<=[.!?])\s+", abstract.strip())
    if len(sentences) <= max_sentences:
        return abstract.strip()

    tokens = tokenize(abstract)
    if not tokens:
        return " ".join(sentences[:max_sentences])

    freq = Counter(tokens)

    scored_sentences: list[tuple[int, float, str]] = []
    for idx, sentence in enumerate(sentences):
        sentence_tokens = tokenize(sentence)
        if not sentence_tokens:
            score = 0.0
        else:
            score = sum(freq[token] for token in sentence_tokens) / len(sentence_tokens)
        scored_sentences.append((idx, score, sentence))

    top = sorted(scored_sentences, key=lambda x: x[1], reverse=True)[:max_sentences]
    top_sorted = sorted(top, key=lambda x: x[0])

    return " ".join(sentence for _, _, sentence in top_sorted)


def compute_relevance_score(
    paper: dict[str, Any],
    user_query: str | None = None,
) -> tuple[float, list[str]]:
    title = clean_text(paper.get("title", ""))
    abstract = clean_text(paper.get("abstract", ""))
    categories = paper.get("categories", [])

    score = 0
    reasons: list[str] = []

    ai_categories = {"cs.AI", "cs.LG", "cs.CL", "cs.CV"}
    matched_ai_categories = [cat for cat in categories if cat in ai_categories]
    if matched_ai_categories:
        category_points = min(30, 15 + 5 * len(matched_ai_categories))
        score += category_points
        reasons.append(
            f"AI categories matched: {', '.join(matched_ai_categories)} (+{category_points})"
        )

    important_keywords = [
        "transformer",
        "language model",
        "llm",
        "multimodal",
        "reasoning",
        "agent",
        "retrieval",
        "diffusion",
        "reinforcement learning",
        "alignment",
        "vision-language",
    ]

    keyword_points = 0
    for keyword in important_keywords:
        if keyword in title:
            keyword_points += 8
            reasons.append(f"Keyword in title: {keyword} (+8)")
        elif keyword in abstract:
            keyword_points += 3
            reasons.append(f"Keyword in abstract: {keyword} (+3)")

    score += min(keyword_points, 30)

    if user_query:
        query_terms = [term for term in tokenize(user_query) if len(term) > 2]
        query_points = 0

        for term in query_terms:
            if term in title:
                query_points += 12
                reasons.append(f"Query term in title: {term} (+12)")
            elif term in abstract:
                query_points += 5
                reasons.append(f"Query term in abstract: {term} (+5)")

        score += min(query_points, 40)

    score = min(score, 100)
    return float(score), reasons


def score_label(score: float) -> str:
    if score >= 80:
        return "Very relevant"
    if score >= 50:
        return "Relevant"
    if score >= 20:
        return "Somewhat relevant"
    return "Weak match"


def categorize_paper(paper: dict[str, Any]) -> str:
    title = clean_text(paper.get("title", ""))
    abstract = clean_text(paper.get("abstract", ""))
    categories = set(paper.get("categories", []))

    best_label = "General AI"
    best_score = -1

    for subdomain, rules in AI_SUBDOMAIN_RULES.items():
        score = 0

        for category in rules["categories"]:
            if category in categories:
                score += 5

        for keyword in rules["keywords"]:
            if keyword in title:
                score += 4
            elif keyword in abstract:
                score += 2

        if score > best_score:
            best_score = score
            best_label = subdomain

    return best_label


def enrich_paper(
    paper: dict[str, Any],
    user_query: str | None = None,
) -> dict[str, Any]:
    summary = summarize_abstract(paper.get("abstract", ""))
    relevance_score, relevance_reasons = compute_relevance_score(
        paper,
        user_query=user_query,
    )
    subdomain = categorize_paper(paper)

    enriched = paper.copy()
    enriched["short_summary"] = summary
    enriched["relevance_score"] = relevance_score
    enriched["relevance_label"] = score_label(relevance_score)
    enriched["relevance_reasons"] = relevance_reasons
    enriched["ai_subdomain"] = subdomain
    return enriched


def analyze_papers(
    papers: list[dict[str, Any]],
    user_query: str | None = None,
) -> list[dict[str, Any]]:
    enriched = [enrich_paper(paper, user_query=user_query) for paper in papers]
    enriched.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    return enriched


def save_analysis_files(
    papers: list[dict[str, Any]],
    query: str,
) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_slug = slugify(query)

    latest_path = OUTPUT_DIR / "arxiv_analysis_latest.json"
    timestamped_path = OUTPUT_DIR / f"arxiv_analysis_{query_slug}_{timestamp}.json"

    with latest_path.open("w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    with timestamped_path.open("w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    return latest_path, timestamped_path


def print_analysis_report(papers: list[dict[str, Any]]) -> None:
    print(f"\nTotal analyzed papers: {len(papers)}")
    if not papers:
        return

    print("\nTop ranked papers:")
    for i, paper in enumerate(papers[:5], start=1):
        print("=" * 100)
        print(f"{i}. {paper['title']}")
        print(f"   Subdomain       : {paper['ai_subdomain']}")
        print(
            f"   Relevance Score : {paper['relevance_score']:.0f}/100 "
            f"({paper['relevance_label']})"
        )
        print(f"   Published       : {paper.get('published_date') or paper.get('published')}")
        print(f"   Categories      : {', '.join(paper.get('categories', [])) or 'N/A'}")
        print(f"   Summary         : {paper['short_summary']}")

        reasons = paper.get("relevance_reasons", [])
        print("   Why ranked      :")
        if reasons:
            for reason in reasons[:5]:
                print(f"      - {reason}")
        else:
            print("      - No strong ranking signals found.")

        print(f"   Abstract URL    : {paper.get('abs_url') or 'N/A'}")
        print(f"   PDF URL         : {paper.get('pdf_url') or 'N/A'}")
        print()


def main() -> None:
    if len(sys.argv) < 2:
        print(
            'Usage: uv run python P3_arxiv_analyze.py "search terms" [max_results] [category] [keyword] [start_date] [end_date]'
        )
        sys.exit(1)

    search_terms = sys.argv[1]

    try:
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    except ValueError:
        print("max_results must be an integer.")
        sys.exit(1)

    category = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "none" else None
    keyword = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "none" else None
    start_date = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "none" else None
    end_date = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "none" else None

    print(f"Running analysis from: {BASE_DIR}")
    print(f"Saving output to     : {OUTPUT_DIR}")

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

        latest_path, timestamped_path = save_analysis_files(analyzed_papers, search_terms)

        print_analysis_report(analyzed_papers)

        print("Saved files:")
        print(f"- {latest_path}")
        print(f"- {timestamped_path}")

    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()