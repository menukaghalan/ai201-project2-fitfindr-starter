"""
app.py

Gradio interface for FitFindr.
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def _format_listing(item: dict | None) -> str:
    if not item:
        return ""

    tags = ", ".join(item.get("style_tags", []))
    colors = ", ".join(item.get("colors", []))
    brand = item.get("brand") or "unbranded"
    return (
        f"{item['title']}\n"
        f"${float(item['price']):g} on {item['platform']} | {item['condition']} condition | size {item['size']}\n"
        f"Brand: {brand}\n"
        f"Colors: {colors}\n"
        f"Tags: {tags}\n\n"
        f"{item['description']}"
    )


def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Returns:
        (listing_text, outfit_suggestion, fit_card)
    """
    if not user_query or not user_query.strip():
        return "Tell me what kind of secondhand piece you want to find.", "", ""

    wardrobe = (
        get_empty_wardrobe()
        if wardrobe_choice == "Empty wardrobe (new user)"
        else get_example_wardrobe()
    )
    session = run_agent(user_query, wardrobe)

    if session["error"]:
        trace = "\n".join(session.get("steps", []))
        return f"{session['error']}\n\nState trace:\n{trace}", "", ""

    listing_text = _format_listing(session["selected_item"])
    outfit_text = session["outfit_suggestion"] or ""
    fit_card_text = session["fit_card"] or ""

    trace = "\n".join(session.get("steps", []))
    if trace:
        fit_card_text = f"{fit_card_text}\n\nState trace:\n{trace}"

    return listing_text, outfit_text, fit_card_text


EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]


def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown(
            """
# FitFindr
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for. Include size and price if you want to filter.
            """
        )

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
