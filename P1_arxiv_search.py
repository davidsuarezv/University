from __future__ import annotations

import sys
from typing import Any

import feedparser
import requests


ARXIV_API_URL = "https://export.arxiv.org/api/query"


def build_search_query(user_terms: str) -> str:
    """
    Build an arXiv search query aimed at AI-related papers.

    Examples:
    - transformer
    - reinforcement learning
    - multimodal reasoning
    """
    # Search across all fields for user terms, and bias toward common AI categories.
    # arXiv query syntax allows fielded search like all:, cat:, ti:, etc.
    escaped_terms = user_terms.strip()
    if not escaped_terms:
        escaped_terms = "artificial intelligence"

    return f'(all:"{escaped_terms}") AND (cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV)'


def fetch_arxiv_papers(
    search_terms: str,
    start: int = 0,
    max_results: int = 5,
    sort_by: str = "submittedDate",
    sort_order: str = "descending",
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """
    Query the arXiv API and return normalized paper metadata.
    """
    search_query = build_search_query(search_terms)

    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }

    response = requests.get(ARXIV_API_URL, params=params, timeout=timeout)
    response.raise_for_status()

    feed = feedparser.parse(response.text)

    papers: list[dict[str, Any]] = []

    for entry in feed.entries:
        authors = [author.name for author in getattr(entry, "authors", [])]

        categories = [tag["term"] for tag in getattr(entry, "tags", [])]

        pdf_url = None
        abs_url = entry.link if hasattr(entry, "link") else None

        for link in getattr(entry, "links", []):
            if getattr(link, "title", "") == "pdf":
                pdf_url = link.href
            elif getattr(link, "rel", "") == "alternate":
                abs_url = link.href

        papers.append(
            {
                "title": entry.title.strip().replace("\n", " "),
                "authors": authors,
                "published": getattr(entry, "published", "N/A"),
                "updated": getattr(entry, "updated", "N/A"),
                "summary": entry.summary.strip().replace("\n", " "),
                "categories": categories,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
            }
        )

    return papers


def print_papers(papers: list[dict[str, Any]]) -> None:
    if not papers:
        print("No papers found.")
        return

    for i, paper in enumerate(papers, start=1):
        print("=" * 80)
        print(f"{i}. {paper['title']}")
        print(f"Authors    : {', '.join(paper['authors']) if paper['authors'] else 'N/A'}")
        print(f"Published  : {paper['published']}")
        print(f"Updated    : {paper['updated']}")
        print(f"Categories : {', '.join(paper['categories']) if paper['categories'] else 'N/A'}")
        print(f"Abstract   : {paper['summary']}")
        print(f"Abstract URL: {paper['abs_url']}")
        print(f"PDF URL     : {paper['pdf_url'] or 'N/A'}")
        print()


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: uv run arxiv_search.py "your search terms" [max_results]')
        sys.exit(1)

    search_terms = sys.argv[1]

    try:
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    except ValueError:
        print("max_results must be an integer.")
        sys.exit(1)

    try:
        papers = fetch_arxiv_papers(
            search_terms=search_terms,
            start=0,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )
        print_papers(papers)

    except requests.HTTPError as exc:
        print(f"HTTP error while calling arXiv: {exc}")
        sys.exit(1)
    except requests.RequestException as exc:
        print(f"Network error while calling arXiv: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()