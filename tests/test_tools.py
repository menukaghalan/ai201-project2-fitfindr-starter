from agent import run_agent
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "graphic" in results[0]["title"].lower() or "tee" in results[0]["title"].lower()


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=50)
    assert all(item["price"] <= 50 for item in results)


def test_search_size_filter_is_flexible():
    results = search_listings("track jacket", size="M", max_price=60)
    assert results
    assert any("M" in item["size"] for item in results)


def test_suggest_outfit_empty_wardrobe_returns_useful_string():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    suggestion = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 30
    assert "I need" not in suggestion


def test_create_fit_card_empty_outfit_returns_error_message():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    fit_card = create_fit_card("", item)
    assert "outfit suggestion" in fit_card


def test_create_fit_card_returns_caption():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    caption = create_fit_card("Pair it with baggy jeans and chunky sneakers.", item)
    assert isinstance(caption, str)
    assert len(caption) > 10
    assert "I need" not in caption


def test_agent_happy_path_uses_state():
    session = run_agent(
        "I'm looking for a vintage graphic tee under $30.",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["outfit_suggestion"]
    assert session["fit_card"]
    assert any("selected_item" in step for step in session["steps"])


def test_agent_no_results_stops_before_downstream_tools():
    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
    assert session["error"]
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
