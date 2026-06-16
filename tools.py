"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

_GROQ_MODEL = "llama-3.3-70b-versatile"


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Tokenize the user's description into lowercase keywords.
    keywords = [word for word in description.lower().split() if word]

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        # --- Filter by price ---
        if max_price is not None and listing["price"] > max_price:
            continue

        # --- Filter by size (case-insensitive substring match) ---
        # e.g. "M" matches "S/M"; skip filtering when size is None or "Any".
        if size is not None and size.strip().lower() not in ("", "any"):
            if size.strip().lower() not in listing["size"].lower():
                continue

        # --- Score by keyword overlap against the listing's searchable text ---
        haystack = " ".join(
            [
                listing["title"],
                listing["description"],
                listing["category"],
                " ".join(listing["style_tags"]),
                " ".join(listing["colors"]),
                listing["brand"] or "",
            ]
        ).lower()

        score = sum(1 for kw in keywords if kw in haystack)

        # --- Drop listings with no keyword relevance ---
        if score > 0:
            scored.append((score, listing))

    # --- Sort by score, highest first, and return the listing dicts ---
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> dict:
    """
    Given a thrifted item and the user's wardrobe, generate a structured outfit
    combination suggestion.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts (the format from get_example_wardrobe()).
                  May be empty — handled gracefully.

    Returns:
        On success, a dict with:
            base_item (str):            title of the newly found item.
            complementary_pieces (list of str): wardrobe item names that pair well.
            styling_rationale (str):    brief paragraph on why it works together.
        If the wardrobe is empty or missing items, a dict with an 'error' key
        describing the failure — does NOT raise an exception.
    """
    items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    if not items:
        return {"error": "Wardrobe profile is empty or missing necessary categories."}

    wardrobe_lines = "\n".join(
        f"- {it.get('name', '')} (category: {it.get('category', 'unknown')}; "
        f"style: {', '.join(it.get('style_tags', []))})"
        for it in items
    )

    prompt = (
        f"The user is considering buying this secondhand item:\n"
        f"  Title: {new_item.get('title', '')}\n"
        f"  Category: {new_item.get('category', '')}\n"
        f"  Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"  Colors: {', '.join(new_item.get('colors', []))}\n\n"
        f"Here is the user's existing wardrobe:\n{wardrobe_lines}\n\n"
        f"Select the wardrobe pieces (by their exact names above) that pair best "
        f"with the new item to build one cohesive outfit, and explain why the "
        f"combination works. Respond with a JSON object containing exactly two keys: "
        f'"complementary_pieces" (a list of the chosen wardrobe item names as strings) '
        f'and "styling_rationale" (a brief paragraph string).'
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a thoughtful personal stylist who builds "
                "outfits from a user's real wardrobe.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    try:
        data = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        return {"error": "Styling response could not be parsed."}

    complementary = [str(p) for p in data.get("complementary_pieces", []) if p]

    return {
        "base_item": new_item.get("title", ""),
        "complementary_pieces": complementary,
        "styling_rationale": str(data.get("styling_rationale", "")),
    }


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # --- 1. Normalize the outfit input into a styling description string ---
    # suggest_outfit() returns a dict, but this tool also accepts a plain
    # string; handle both so the agent loop never crashes on the hand-off.
    if isinstance(outfit, dict):
        if "error" in outfit:
            return "Couldn't generate a caption — no valid outfit was provided."
        pieces = outfit.get("complementary_pieces", [])
        rationale = outfit.get("styling_rationale", "")
        outfit_text = "\n".join(
            [
                f"Pairs with: {', '.join(pieces)}" if pieces else "",
                f"Styling notes: {rationale}" if rationale else "",
            ]
        ).strip()
    else:
        outfit_text = str(outfit or "").strip()

    # Guard against an empty or whitespace-only outfit.
    if not outfit_text:
        return "Couldn't generate a caption — no outfit details were provided."

    # --- 2. Build the caption prompt with the item details and the outfit ---
    title = new_item.get("title", "this piece") if isinstance(new_item, dict) else "this piece"
    price = new_item.get("price") if isinstance(new_item, dict) else None
    platform = new_item.get("platform", "") if isinstance(new_item, dict) else ""

    price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "a steal"

    prompt = (
        f"Write a short, casual social-media caption (2-4 sentences) for an "
        f"outfit built around a secondhand find.\n\n"
        f"Item: {title}\n"
        f"Price: {price_str}\n"
        f"Platform: {platform or 'a thrift app'}\n"
        f"Outfit details:\n{outfit_text}\n\n"
        f"Guidelines:\n"
        f"- Sound like a real OOTD/thrift-haul post, NOT a product description.\n"
        f"- Mention the item name, the price, and the platform naturally, once each.\n"
        f"- Capture the specific vibe of the outfit.\n"
        f"- Keep it to 2-4 sentences. A tasteful emoji or two is fine.\n"
        f"- Return only the caption text, no quotes or labels."
    )

    # --- 3. Call the LLM (higher temperature for variety) and return the text ---
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You write punchy, authentic captions for "
                    "secondhand fashion finds.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
        )
        caption = (response.choices[0].message.content or "").strip()
    except Exception as exc:  # network/API failure — degrade gracefully
        return f"Found {title} for {price_str}. (Caption unavailable: {exc})"

    if not caption:
        return f"Snagged {title} for {price_str} — a perfect thrifted score."

    return caption
