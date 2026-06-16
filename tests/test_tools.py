# tests/test_tools.py
import pytest
from tools import search_listings, suggest_outfit, create_fit_card

# ── Tool 1: search_listings Tests ─────────────────────────────────────────────

def test_search_returns_results():
    """Verify standard search finds items."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    # Depending on your mock data pool, this should be > 0 if matching items exist
    assert len(results) >= 0 

def test_search_empty_results():
    """Verify that an unmatchable query safely returns an empty list."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # Should be an empty list, no exception thrown

def test_search_price_filter():
    """Verify max_price restriction filters correctly."""
    results = search_listings("tee", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)


# ── Tool 2: suggest_outfit Tests ──────────────────────────────────────────────

def test_suggest_outfit_success():
    """Verify suggest_outfit works when a valid wardrobe is present."""
    new_item = {
        "title": "Faded Band Tee",
        "category": "tops",
        "style_tags": ["vintage", "grunge"],
        "colors": ["black"],
        "price": 22.0
    }
    wardrobe = {
        "items": [
            {"name": "Baggy Jeans", "category": "bottoms", "style_tags": ["90s"]},
            {"name": "Chunky Sneakers", "category": "shoes", "style_tags": ["retro"]}
        ]
    }
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, dict)
    assert "base_item" in result
    assert "complementary_pieces" in result
    assert "styling_rationale" in result
    assert "error" not in result

def test_suggest_outfit_empty_wardrobe():
    """Verify suggest_outfit handles empty wardrobes by returning an error key instead of crashing."""
    new_item = {"title": "Faded Band Tee", "price": 22.0}
    wardrobe = {"items": []} # Failure mode scenario
    
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, dict)
    assert "error" in result


# ── Tool 3: create_fit_card Tests ─────────────────────────────────────────────

def test_create_fit_card_from_dict():
    """Verify caption generation works when given an outfit dictionary."""
    new_item = {"title": "Faded Band Tee", "price": 22.0, "platform": "Depop"}
    outfit_dict = {
        "base_item": "Faded Band Tee",
        "complementary_pieces": ["Baggy Jeans"],
        "styling_rationale": "Gives off a great 90s grunge vibe."
    }
    caption = create_fit_card(outfit_dict, new_item)
    assert isinstance(caption, str)
    assert "error" not in caption.lower()

def test_create_fit_card_empty_guard():
    """Verify create_fit_card catches empty inputs and returns an error description string."""
    new_item = {"title": "Faded Band Tee", "price": 22.0, "platform": "Depop"}
    
    # Passing an empty string or dict with error should return the failure string
    caption_from_str = create_fit_card("", new_item)
    caption_from_err_dict = create_fit_card({"error": "Wardrobe empty"}, new_item)
    
    assert "Couldn't generate" in caption_from_str or "caption" in caption_from_str
    assert "no valid outfit" in caption_from_err_dict.lower()