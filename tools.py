"""
tools.py

The three required FitFindr tools. Each function can be tested in isolation
before being wired into the agent loop.
"""

import os
import random
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _groq_model() -> str:
    return os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _normalize(value) -> str:
    return str(value or "").strip().lower()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _normalize(text)))


def _listing_text(listing: dict) -> str:
    fields = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        listing.get("brand") or "",
        listing.get("platform", ""),
        " ".join(listing.get("style_tags", [])),
        " ".join(listing.get("colors", [])),
    ]
    return " ".join(fields)


def _size_matches(listing_size: str, requested_size: str | None) -> bool:
    if not requested_size:
        return True

    listing = _normalize(listing_size)
    requested = _normalize(requested_size)
    if not requested:
        return True
    if listing == requested:
        return True

    listing_parts = set(re.findall(r"[a-z0-9.]+", listing))
    requested_parts = set(re.findall(r"[a-z0-9.]+", requested))
    return bool(listing_parts & requested_parts)


def _call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str | None:
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_groq_model(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=260,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Returns an empty list if nothing matches or if loading/searching fails.
    """
    try:
        listings = load_listings()
    except (OSError, ValueError):
        return []

    query_tokens = _tokens(description)
    if not query_tokens:
        return []

    try:
        price_limit = float(max_price) if max_price is not None else None
    except (TypeError, ValueError):
        price_limit = None

    matches = []
    for listing in listings:
        if price_limit is not None and float(listing.get("price", 0)) > price_limit:
            continue
        if not _size_matches(listing.get("size", ""), size):
            continue

        searchable_text = _listing_text(listing)
        listing_tokens = _tokens(searchable_text)
        overlap = query_tokens & listing_tokens
        phrase_bonus = 3 if _normalize(description) in _normalize(searchable_text) else 0
        tag_bonus = sum(
            2 for tag in listing.get("style_tags", [])
            if _normalize(tag) in _normalize(description)
        )
        title_bonus = len(query_tokens & _tokens(listing.get("title", "")))
        score = len(overlap) + phrase_bonus + tag_bonus + title_bonus

        if score > 0:
            result = dict(listing)
            result["relevance_score"] = score
            matches.append(result)

    return sorted(matches, key=lambda item: (-item["relevance_score"], item["price"]))


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    Empty wardrobes receive general styling advice instead of an exception.
    """
    if not isinstance(new_item, dict) or not new_item.get("title"):
        return "I need a valid thrift listing before I can suggest an outfit."

    wardrobe_items = (wardrobe or {}).get("items", [])
    item_details = (
        f"{new_item.get('title')} | category: {new_item.get('category')} | "
        f"colors: {', '.join(new_item.get('colors', []))} | "
        f"tags: {', '.join(new_item.get('style_tags', []))}"
    )

    if wardrobe_items:
        wardrobe_text = "\n".join(
            "- {name} ({category}; colors: {colors}; tags: {tags}; notes: {notes})".format(
                name=item.get("name", "Unnamed item"),
                category=item.get("category", "unknown"),
                colors=", ".join(item.get("colors", [])),
                tags=", ".join(item.get("style_tags", [])),
                notes=item.get("notes") or "none",
            )
            for item in wardrobe_items
        )
        user_prompt = (
            f"New thrift find:\n{item_details}\n\n"
            f"User wardrobe:\n{wardrobe_text}\n\n"
            "Suggest one complete outfit using the new item and named wardrobe pieces. "
            "Keep it specific, wearable, and 2-4 sentences."
        )
    else:
        user_prompt = (
            f"New thrift find:\n{item_details}\n\n"
            "The user has not added wardrobe items yet. Suggest a complete outfit using "
            "general basics most people might own. Keep it specific and 2-4 sentences."
        )

    llm_output = _call_llm(
        "You are FitFindr, a concise stylist for secondhand fashion.",
        user_prompt,
        temperature=0.75,
    )
    if llm_output:
        return llm_output

    if not wardrobe_items:
        return (
            f"Style the {new_item['title']} with a simple base: relaxed denim or a clean black skirt, "
            "comfortable sneakers or loafers, and one small accessory. Keep the rest of the outfit simple "
            "so the thrifted piece feels intentional."
        )

    by_category = {}
    for item in wardrobe_items:
        by_category.setdefault(item.get("category"), item)

    bottoms = by_category.get("bottoms", {"name": "your easiest jeans"})
    shoes = by_category.get("shoes", {"name": "simple sneakers"})
    layer = by_category.get("outerwear")
    accessory = by_category.get("accessories")

    suggestion = f"Pair the {new_item['title']} with {bottoms['name']} and {shoes['name']}."
    if layer:
        suggestion += f" Add {layer['name']} if you want more structure or warmth."
    if accessory:
        suggestion += f" Finish with {accessory['name']} so the outfit feels complete."
    suggestion += " Balance the silhouette by letting one piece stay relaxed and keeping the others cleaner."
    return suggestion


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    If outfit is empty or missing, return a descriptive error string.
    """
    if not outfit or not str(outfit).strip():
        return "I need an outfit suggestion before I can write a fit card."
    if not isinstance(new_item, dict) or not new_item.get("title"):
        return "I need a valid thrift find before I can write a fit card."

    user_prompt = (
        f"Item: {new_item.get('title')}\n"
        f"Price: ${float(new_item.get('price', 0)):g}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Outfit suggestion: {outfit}\n\n"
        "Write one casual OOTD caption under 45 words. Mention the item, price, "
        "and platform naturally once. Do not sound like a product listing."
    )
    llm_output = _call_llm(
        "You write varied, natural social captions for thrifted outfits.",
        user_prompt,
        temperature=1.0,
    )
    if llm_output:
        return llm_output

    openers = [
        "secondhand score",
        "thrift math worked out",
        "found the missing piece",
        "today's fit started here",
    ]
    details = [
        "built around pieces I already reach for",
        "soft, lived-in, and very easy to repeat",
        "the kind of find that makes the whole outfit click",
        "proof that a saved search can carry the look",
    ]
    return (
        f"{random.choice(openers)}: {new_item['title'].lower()} from "
        f"{new_item.get('platform')} for ${float(new_item.get('price', 0)):g}, "
        f"{random.choice(details)}."
    )


def compare_price(item: dict, listings: list[dict] | None = None) -> dict:
    """Stretch tool: compare an item price against similar category listings."""
    if not isinstance(item, dict) or "price" not in item:
        return {"status": "error", "message": "A priced item is required for comparison."}

    listings = listings or load_listings()
    comparable = [
        listing for listing in listings
        if listing.get("id") != item.get("id") and listing.get("category") == item.get("category")
    ]
    if not comparable:
        return {"status": "unknown", "message": "No comparable listings were available."}

    avg_price = sum(float(listing["price"]) for listing in comparable) / len(comparable)
    item_price = float(item["price"])
    if item_price <= avg_price * 0.9:
        verdict = "good deal"
    elif item_price >= avg_price * 1.15:
        verdict = "pricey"
    else:
        verdict = "fair"

    return {
        "status": "ok",
        "verdict": verdict,
        "item_price": item_price,
        "average_comparable_price": round(avg_price, 2),
        "comparable_count": len(comparable),
    }
