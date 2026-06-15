# FitFindr

FitFindr is a multi-tool AI agent for secondhand shopping. It searches mock thrift listings, chooses a useful match, suggests how to style it with a user's wardrobe, and creates a short shareable fit card.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

## Run the App

```bash
python app.py
```

Open the Gradio URL printed in the terminal.

## Run Tests

```bash
pytest tests/
```

## Tool Inventory

`search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]`

Purpose: Searches `data/listings.json` for items that match the user's request. It filters by optional `size` and `max_price`, scores keyword relevance across title, description, category, tags, colors, brand, and platform, and returns sorted listing dictionaries. Output listings include the original dataset fields plus `relevance_score`.

`suggest_outfit(new_item: dict, wardrobe: dict) -> str`

Purpose: Suggests a complete outfit for the selected listing. With a populated wardrobe, it asks Groq to use named wardrobe pieces. With an empty wardrobe, it asks for general styling advice. If the LLM call fails, a local fallback still returns useful styling text.

`create_fit_card(outfit: str, new_item: dict) -> str`

Purpose: Generates a short OOTD-style caption from the outfit suggestion and thrift listing. It mentions the item, price, platform, and vibe. If `outfit` is empty, it returns a descriptive error string instead of crashing.

`compare_price(item: dict, listings: list[dict] | None = None) -> dict`

Stretch tool. Compares a listing's price with other items in the same category and returns whether it is a `good deal`, `fair`, `pricey`, or `unknown`.

## Planning Loop

The planning loop lives in `run_agent(query, wardrobe)` in `agent.py`.

1. Initialize a session dictionary.
2. Parse the query into `description`, `size`, and `max_price`.
3. Call `search_listings`.
4. If search returns no results, set `session["error"]` and return immediately.
5. If search succeeds, store the first result in `session["selected_item"]`.
6. Call `suggest_outfit` with `session["selected_item"]` and `session["wardrobe"]`.
7. Store that string in `session["outfit_suggestion"]`.
8. Call `create_fit_card` with `session["outfit_suggestion"]` and `session["selected_item"]`.
9. Store the caption in `session["fit_card"]` and return the session.

The important branch is after search: the agent does not blindly call every tool if there is no selected item.

## State Management

State is stored in one session dictionary. The selected listing returned by search becomes `session["selected_item"]`, and that exact dictionary is passed to both `suggest_outfit` and `create_fit_card`. The outfit text from `suggest_outfit` becomes `session["outfit_suggestion"]`, and that exact string is passed into `create_fit_card`. The UI displays a `steps` trace so the demo can show state moving between tools.

## Error Handling

Search failure: `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`. The agent sets an error message telling the user to broaden the description, raise max price, or remove the size filter. It leaves `selected_item`, `outfit_suggestion`, and `fit_card` as `None`.

Empty wardrobe: `suggest_outfit(item, get_empty_wardrobe())` returns general styling advice using common basics. The agent continues because a usable outfit string exists.

Missing outfit: `create_fit_card("", item)` returns `"I need an outfit suggestion before I can write a fit card."` The agent normally avoids this because it only calls fit-card generation after outfit generation.

## Spec Reflection

The spec helped most by forcing the planning loop to branch on search results. That made it clear the agent needed a session object and an early-return path instead of a fixed sequence.

One implementation detail that diverged slightly from the initial starter is the visible state trace in the fit-card panel. The project only requires state passing to be shown in the demo, but exposing it in the app makes that easier to narrate and verify.

## AI Usage

First, I used the Tool 1, Tool 2, and Tool 3 sections of `planning.md` as prompts for implementing `tools.py`. I revised the search implementation to support flexible size matching because the starter dataset uses sizes like `S/M`, `M/L`, and `US 8`.

Second, I used the Planning Loop, State Management, and Architecture sections to implement `run_agent()` in `agent.py`. I checked the generated loop to confirm the no-results branch returns before outfit or fit-card tools run.

Third, I used the Error Handling table to create pytest cases for search failure, empty wardrobe, empty outfit input, and the full agent no-results path.
