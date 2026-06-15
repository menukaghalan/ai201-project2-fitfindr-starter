"""
agent.py

The FitFindr planning loop. Orchestrates the tools in response to a natural
language user query, passing state between them via a session dict.
"""

import re

from tools import create_fit_card, search_listings, suggest_outfit


def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize a fresh session dict for one user interaction."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
        "steps": [],
    }


def _parse_query(query: str) -> dict:
    """Extract a practical description, optional size, and optional max price."""
    text = query or ""
    lowered = text.lower()

    max_price = None
    price_match = re.search(
        r"(?:under|below|less than|up to|max(?:imum)?|budget(?: is)?|for)\s*\$?(\d+(?:\.\d+)?)",
        lowered,
    )
    if not price_match:
        price_match = re.search(r"\$(\d+(?:\.\d+)?)", lowered)
    if price_match:
        max_price = float(price_match.group(1))

    size = None
    size_match = re.search(r"\bsize\s+([a-z0-9./-]+)\b", lowered)
    if size_match:
        size = size_match.group(1).upper()

    description = re.sub(r"\bsize\s+[a-z0-9./-]+\b", " ", text, flags=re.IGNORECASE)
    description = re.sub(
        r"(?:under|below|less than|up to|max(?:imum)?|budget(?: is)?|for)\s*\$?\d+(?:\.\d+)?",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\$\d+(?:\.\d+)?", " ", description)
    description = " ".join(description.split()).strip()

    return {
        "description": description or text,
        "size": size,
        "max_price": max_price,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed
    session["steps"].append(f"Parsed query into {parsed}.")

    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results
    session["steps"].append(f"search_listings returned {len(results)} result(s).")

    if not results:
        session["error"] = (
            "I could not find a matching secondhand listing. Try broadening the item description, "
            "raising your max price, or removing the size filter."
        )
        session["steps"].append("Stopped early because search returned no usable listing.")
        return session

    selected_item = results[0]
    session["selected_item"] = selected_item
    session["steps"].append(f"Selected top listing: {selected_item['title']}.")

    outfit = suggest_outfit(selected_item, session["wardrobe"])
    session["outfit_suggestion"] = outfit
    session["steps"].append("Passed selected_item and wardrobe into suggest_outfit.")

    if not outfit or outfit.startswith("I need"):
        session["error"] = outfit or "The outfit tool did not return a useful suggestion."
        session["steps"].append("Stopped before fit card because outfit generation failed.")
        return session

    fit_card = create_fit_card(outfit, selected_item)
    session["fit_card"] = fit_card
    session["steps"].append("Passed outfit_suggestion and selected_item into create_fit_card.")

    return session


if __name__ == "__main__":
    from utils.data_loader import get_empty_wardrobe, get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
        print(f"\nSteps: {session['steps']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_empty_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"Fit card: {session2['fit_card']}")
