# FitFindr — AI Thrift Shopping Agent

FitFindr is an AI-powered secondhand shopping assistant. You describe what you're looking for, and the agent searches mock thrift listings, suggests how the find pairs with your existing wardrobe, and generates a shareable fit card caption — all in one sequential pipeline.

---

## Tool Inventory

### `search_listings(description, size=None, max_price=None)`
Searches the JSON dataset using a keyword scoring approach. The description is split into lowercase tokens, each listing is scored by how many keywords overlap with its title, description, and style tags, zero-relevance matches are dropped, and results are returned sorted highest score first. Optional `size` and `max_price` filters narrow the pool before scoring runs.

### `suggest_outfit(new_item, wardrobe)`
Formats the user's wardrobe items into a readable text block and sends it alongside the new listing to Groq's `llama-3.3-70b-versatile` model. Returns a dictionary with two keys:
- `complementary_pieces` — wardrobe items that pair well with the find
- `styling_rationale` — a short explanation of why the pairing works

If the wardrobe is empty, the function safely returns a dict containing an `error` key instead of raising an exception.

### `create_fit_card(outfit, new_item)`
Takes the outfit suggestion and the listing details and produces a short, casual 2–4 sentence social media caption. The caption mentions the item name, price, and platform exactly once each. Uses `temperature=0.9` so each generated caption comes out distinct. Accepts either a dict (from `suggest_outfit`) or a raw string.

---

## Planning Loop — How `run_agent()` Works

`run_agent()` in `agent.py` coordinates the three tools in a strict sequential pipeline:

1. **Parse filters** — the natural language input string is scanned for size constraints and price limits before anything else runs.
2. **Search** — `search_listings` is called with the parsed filters. If the result list is empty, the agent halts immediately and tells the user to try loosening their filters. No further tools are called.
3. **Extract top item** — the highest-scored listing is pulled from the results list.
4. **Suggest outfit** — the top item and the current wardrobe are passed to `suggest_outfit`. If the returned dict contains an `error` key (empty wardrobe case), the agent halts and prompts the user to add wardrobe pieces first.
5. **Generate fit card** — the suggestion dict and item details are handed to `create_fit_card`, which produces the final caption.

Each step only runs if the previous one succeeded. There are no silent failures — every dead-end returns a readable message to the user.

---

## State Management

A centralized `session` dictionary acts as the single source of truth throughout a run. Individual tools are stateless — they take inputs, return outputs, and have no awareness of each other. The orchestrator (`run_agent`) pulls each tool's output from the session, converts or reformats it as needed, feeds it as a parameter into the next function, and writes the result back into the session. Nothing is shared between tools directly; all coordination flows through the session object.

---

## Error Handling

Each tool has its own guard against bad inputs, and each failure is handled gracefully at the agent level rather than crashing the whole script.

**`search_listings` — no matching results**
```
>>> search_listings('designer ballgown', size='XXS', max_price=5)
[]
```
Calling with a very restrictive combination like size `XXS` and a $5 price ceiling returns an empty list cleanly — no exception is raised. The agent detects the empty list, stops execution, and returns a message like: *"No listings matched your filters. Try broadening your search or raising your budget."*

**`suggest_outfit` — empty wardrobe**
```
>>> suggest_outfit(item, get_empty_wardrobe())
{'error': 'Wardrobe is empty. Please add some pieces first.'}
```
When the wardrobe passed in has no items, the function traps the missing items array before calling the LLM and returns a dict with an `error` key. The agent checks for this key and halts with a prompt to add wardrobe pieces rather than letting a Python error bubble up.

**`create_fit_card` — empty outfit string**
```
>>> create_fit_card('', item)
'Could not generate a fit card — outfit description was empty.'
```
An empty string hits a guard clause at the top of the function before any API call is made. The function returns a friendly fallback message rather than passing a blank prompt to the model and getting a nonsensical caption.

---

## Reflection on the Spec

The final application closely follows the original plan. One meaningful deviation came up during implementation: the data type flowing from `suggest_outfit` into `create_fit_card` is not always consistent. In some paths the outfit comes back as a fully structured dictionary; in others it arrives as a plain string. To protect the agent loop from crashing at that hand-off, `create_fit_card` was modified to check `isinstance(outfit, dict)` and extract the relevant fields accordingly before building the caption. This was a small but necessary deviation from the original spec.

---

## AI Usage

**Instance 1 — Keyword Scoring Algorithm in `tools.py`**
I passed the initial markdown specification block for `search_listings` into Claude and asked it to generate the standalone keyword scoring and threshold logic. The generated algorithm split descriptions into lowercase tokens, scored each listing by overlap count, and filtered out zero-relevance results. After reviewing the output, I also increased the Groq API temperature for `create_fit_card` up to `0.9` to ensure the social media captions came out varied rather than templated.

**Instance 2 — Conditional Control Flow in `agent.py`**
I provided the sequential control specifications and architecture details to Claude/Copilot to scaffold the conditional branching inside `run_agent()`. The generated structure covered the empty-results halt and the LLM call chain, but I overrode the generated error-handling section to explicitly check for the `error` key in the `suggest_outfit` return value before passing any data forward to `create_fit_card`. The AI-generated version assumed a successful dict structure at every step; I added the explicit key check to make the halting behavior intentional and user-friendly.

---
