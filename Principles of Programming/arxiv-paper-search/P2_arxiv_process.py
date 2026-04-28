from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from P1_arxiv_search import fetch_arxiv_papers


def parse_arxiv_date(date_str: str) -> datetime | None:
    """
    Convert arXiv date string like:
    2026-04-18T12:34:56Z
    into a Python datetime object.
    """
    if not date_str or date_str == "N/A":
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def normalize_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """
    Extract and standardize only the metadata we care about.
    """
    published_dt = parse_arxiv_date(paper.get("published", ""))
    updated_dt = parse_arxiv_date(paper.get("updated", ""))

    return {
        "title": paper.get("title", "").strip(),
        "authors": paper.get("authors", []),
        "abstract": paper.get("summary", "").strip(),
        "categories": paper.get("categories", []),
        "published": paper.get("published", "N/A"),
        "updated": paper.get("updated", "N/A"),
        "published_date": published_dt.date().isoformat() if published_dt else None,
        "updated_date": updated_dt.date().isoformat() if updated_dt else None,
        "abs_url": paper.get("abs_url"),
        "pdf_url": paper.get("pdf_url"),
    }


def normalize_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_paper(paper) for paper in papers]


def filter_papers(
    papers: list[dict[str, Any]],
    category: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    Filter papers by:
    - category (exact match in categories list)
    - keyword (case-insensitive search in title + abstract)
    - date range (based on published_date)
    """
    filtered = papers

    if category:
        filtered = [
            paper for paper in filtered
            if category in paper.get("categories", [])
        ]

    if keyword:
        keyword_lower = keyword.lower()
        filtered = [
            paper for paper in filtered
            if keyword_lower in paper.get("title", "").lower()
            or keyword_lower in paper.get("abstract", "").lower()
        ]

    if start_date:
        filtered = [
            paper for paper in filtered
            if paper.get("published_date") and paper["published_date"] >= start_date
        ]

    if end_date:
        filtered = [
            paper for paper in filtered
            if paper.get("published_date") and paper["published_date"] <= end_date
        ]

    return filtered


def save_to_json(papers: list[dict[str, Any]], output_file: str) -> None:
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)


def save_to_csv(papers: list[dict[str, Any]], output_file: str) -> None:
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "title",
        "authors",
        "abstract",
        "categories",
        "published",
        "updated",
        "published_date",
        "updated_date",
        "abs_url",
        "pdf_url",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for paper in papers:
            row = paper.copy()
            row["authors"] = "; ".join(row.get("authors", []))
            row["categories"] = "; ".join(row.get("categories", []))
            writer.writerow(row)


def print_summary(papers: list[dict[str, Any]]) -> None:
    print(f"Total papers after processing/filtering: {len(papers)}")

    if not papers:
        return

    print("\nSample results:")
    for i, paper in enumerate(papers[:3], start=1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Authors   : {', '.join(paper['authors']) if paper['authors'] else 'N/A'}")
        print(f"   Published : {paper['published_date'] or paper['published']}")
        print(f"   Categories: {', '.join(paper['categories']) if paper['categories'] else 'N/A'}")


def main() -> None:
    """
    Example usage:

    uv run arxiv_process.py "transformer" 20
    uv run arxiv_process.py "multimodal reasoning" 25 cs.CL attention 2025-01-01 2026-12-31
    """
    if len(sys.argv) < 2:
        print(
            'Usage: uv run arxiv_process.py "search terms" [max_results] [category] [keyword] [start_date] [end_date]'
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

        save_to_json(filtered_papers, "output/arxiv_results.json")
        save_to_csv(filtered_papers, "output/arxiv_results.csv")

        print_summary(filtered_papers)
        print("\nSaved files:")
        print("- output/arxiv_results.json")
        print("- output/arxiv_results.csv")

    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()