# FitFindr Planning

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset for items that match the user's description, optional size, and optional max price. It scores possible matches by keyword overlap across title, description, category, style tags, colors, brand, and platform.

**Input parameters:**
- `description` (str): Natural language description of the desired item, such as `"vintage graphic tee"`.
- `size` (str | None): Optional size filter. Matching is flexible enough for `"M"` to match starter data values like `"S/M"` or `"M/L"`.
- `max_price` (float | None): Optional maximum price, inclusive.

**What it returns:**
A `list[dict]` of matching listing dictionaries sorted by highest relevance and then lowest price. Each result contains the starter fields `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`, plus a computed `relevance_score`.

**What happens if it fails or returns nothing:**
The tool returns `[]` instead of raising an exception. The agent checks for the empty list, sets `session["error"]`, tells the user to broaden the description, raise the price, or remove the size filter, and stops before calling outfit generation.

---

### Tool 2: suggest_outfit

**What it does:**
Uses the selected thrift listing and the user's wardrobe to suggest a complete outfit. If a Groq key is available, it uses `llama-3.3-70b-versatile`; otherwise it falls back to a deterministic local suggestion so the app and tests still run.

**Input parameters:**
- `new_item` (dict): The selected listing dictionary from `search_listings`.
- `wardrobe` (dict): A wardrobe dictionary with an `items` list from `wardrobe_schema.json`.

**What it returns:**
A non-empty string with a wearable outfit suggestion. With a populated wardrobe, it names specific wardrobe pieces. With an empty wardrobe, it suggests common basics and styling details.

**What happens if it fails or returns nothing:**
If `new_item` is invalid, the tool returns an explanatory string beginning with `"I need..."`. If the wardrobe is empty, it still returns useful general advice rather than failing.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion and selected listing into a short, shareable OOTD-style caption.

**Input parameters:**
- `outfit` (str): The outfit suggestion returned by `suggest_outfit`.
- `new_item` (dict): The selected thrift listing dictionary.

**What it returns:**
A caption string under roughly 45 words that mentions the thrifted item, platform, price, and outfit vibe. The LLM call uses a higher temperature for variation; the local fallback uses randomized caption templates.

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace-only, it returns `"I need an outfit suggestion before I can write a fit card."` If `new_item` is invalid, it returns `"I need a valid thrift find before I can write a fit card."`

---

### Additional Tools

#### compare_price

**What it does:**
Stretch tool that compares an item's price with other listings in the same category.

**Input parameters:**
- `item` (dict): A listing dictionary with a `price` and `category`.
- `listings` (list[dict] | None): Optional comparable listing set. If omitted, it loads the mock dataset.

**What it returns:**
A dictionary with `status`, `verdict`, `item_price`, `average_comparable_price`, and `comparable_count`, or an error/unknown message if comparison is impossible.

**What happens if it fails or returns nothing:**
It returns a structured error dictionary instead of raising.

---

## Planning Loop

The agent uses `run_agent(query, wardrobe)` as a conditional planning loop:

1. Create a session dictionary with the original query, parsed parameters, search results, selected item, wardrobe, outfit suggestion, fit card, error, and step trace.
2. Parse the query with regex into `description`, `size`, and `max_price`.
3. Call `search_listings(description, size, max_price)`.
4. If search returns `[]`, set `session["error"]` to a helpful message and return immediately. The agent does not call `suggest_outfit` or `create_fit_card`.
5. If search returns results, store the top result in `session["selected_item"]`.
6. Call `suggest_outfit(session["selected_item"], session["wardrobe"])`.
7. Store the result in `session["outfit_suggestion"]`.
8. If the outfit result is empty or an invalid-input message, set `session["error"]` and return before fit-card generation.
9. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
10. Store the result in `session["fit_card"]` and return the session.

---

## State Management

The session dictionary is the single source of truth during one interaction. It stores:

- `query`: Original user request.
- `parsed`: Extracted `description`, `size`, and `max_price`.
- `search_results`: All listing matches from search.
- `selected_item`: The top result that gets passed to styling and fit-card tools.
- `wardrobe`: The example or empty wardrobe selected in the UI.
- `outfit_suggestion`: The output from `suggest_outfit`.
- `fit_card`: The output from `create_fit_card`.
- `error`: A message when the loop stops early.
- `steps`: A visible trace of the planning loop for debugging and demo narration.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Store a helpful error in `session["error"]`, leave downstream state as `None`, and tell the user to broaden the description, raise max price, or remove size. |
| suggest_outfit | Wardrobe is empty | Return general styling advice with common basics; the agent continues to fit-card generation because the output is useful. |
| suggest_outfit | New item is missing or invalid | Return an `"I need..."` message; the agent stores it as an error and stops before creating a fit card. |
| create_fit_card | Outfit input is missing or incomplete | Return `"I need an outfit suggestion before I can write a fit card."` The direct tool test verifies this path. |

---

## Architecture

```mermaid
flowchart TD
    U[User query] --> P[Planning loop]
    P --> Q[Parse query into description, size, max_price]
    Q --> S[search_listings]
    S -->|results empty| E[Set session.error and return]
    S -->|results found| ST1[session.selected_item = results[0]]
    ST1 --> O[suggest_outfit]
    O --> ST2[session.outfit_suggestion = outfit]
    ST2 -->|invalid outfit| E
    ST2 --> C[create_fit_card]
    C --> ST3[session.fit_card = caption]
    ST3 --> R[Return session]
    E --> R
```

---

## AI Tool Plan

**Milestone 3 - Individual tool implementations:**
I will give Codex the Tool 1, Tool 2, and Tool 3 sections one at a time and ask it to implement each function in `tools.py` using `load_listings()` from the data loader. I will verify that search filters by description, size, and price; that outfit generation handles empty wardrobes; and that fit-card generation handles empty outfit strings. Then I will test each tool directly and with pytest.

**Milestone 4 - Planning loop and state management:**
I will give Codex the Planning Loop, State Management, and Architecture sections and ask it to implement `run_agent()` in `agent.py`. I will verify that the no-results branch returns early and that downstream tools receive data from `session["selected_item"]` and `session["outfit_suggestion"]`.

**Milestone 5 - Failure-mode tests:**
I will give Codex the Error Handling table and ask it to create pytest cases for no search results, empty wardrobe, and empty outfit input. I will verify that tests assert behavior rather than exact LLM prose because LLM outputs may vary.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query into `description="I'm looking for a vintage graphic tee. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"`, `size=None`, and `max_price=30.0`.

**Step 2:**
The agent calls `search_listings(description, size=None, max_price=30.0)`. It receives matching items such as `"Graphic Tee - 2003 Tour Bootleg Style"` and `"Vintage Band Tee - Faded Grey"`, sorted by relevance and price.

**Step 3:**
The agent stores the top result in `session["selected_item"]`. This full listing dictionary is now available to later tools.

**Step 4:**
The agent calls `suggest_outfit(session["selected_item"], session["wardrobe"])`. The outfit tool uses the selected thrift item plus wardrobe pieces such as baggy jeans, chunky sneakers, boots, a black denim jacket, or accessories.

**Step 5:**
The agent stores the returned styling text in `session["outfit_suggestion"]`.

**Step 6:**
The agent calls `create_fit_card(session["outfit_suggestion"], session["selected_item"])`. It returns a short caption mentioning the item, price, platform, and outfit vibe.

**Final output to user:**
The Gradio app shows the selected listing in the first panel, the styling suggestion in the second panel, and the fit card plus a state trace in the third panel. If search had returned no results, the first panel would show the error message and the other panels would stay empty.
