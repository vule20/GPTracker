"""
debug_extractor.py
Created: 2025-11-13 15:52
Author: VuLe@UMass Amherst
Last updated: 2025-11-13 15:52
Last modified by: VuLe@UMass Amherst
License: © Copyright 2025, Vu Le
Desc:
"""

#!/usr/bin/env python3
"""
Debug Single GPT Extraction
Test metadata extraction on a single GPT to see what's being captured
"""

import asyncio
import json
from playwright.async_api import async_playwright


async def debug_single_gpt(gizmo_id: str):
    """
    Debug metadata extraction for a single GPT
    Shows exactly what data is found
    """
    url = f"https://chatgpt.com/g/{gizmo_id}"

    print(f"🔍 Debugging GPT: {gizmo_id}")
    print(f"📍 URL: {url}")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate
            print("\n1️⃣ Loading page...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(4)

            # Get full text
            print("\n2️⃣ Extracting full text...")
            full_text = await page.evaluate("() => document.body.innerText")
            print(f"   Text length: {len(full_text)} characters")
            print(f"   First 500 chars:\n   {full_text[:500]}")

            # Get headings
            print("\n3️⃣ Finding headings (GPT name)...")
            headings = await page.query_selector_all("h1, h2, h3")
            for i, h in enumerate(headings[:5]):
                text = await h.text_content()
                print(f"   Heading {i+1}: {text.strip()}")

            # Get paragraphs
            print("\n4️⃣ Finding paragraphs (description)...")
            paragraphs = await page.query_selector_all("p")
            for i, p in enumerate(paragraphs[:5]):
                text = await p.text_content()
                if len(text.strip()) > 30:
                    print(f"   Paragraph {i+1}: {text.strip()[:100]}...")

            # Get buttons
            print("\n5️⃣ Finding buttons (conversation starters)...")
            buttons = await page.query_selector_all("button")
            for i, b in enumerate(buttons[:10]):
                text = await b.text_content()
                if text and len(text.strip()) > 10:
                    print(f"   Button {i+1}: {text.strip()}")

            # Pattern matching
            print("\n6️⃣ Pattern matching in text...")
            import re

            # Find "By X" pattern
            by_matches = re.findall(
                r"[Bb]y\s+([A-Za-z0-9\s\.]+?)(?:\n|\||$)", full_text
            )
            if by_matches:
                print(f"   Author candidates: {by_matches[:3]}")

            # Find quoted strings (potential starters)
            quote_matches = re.findall(r'"([^"]{20,200})"', full_text)
            if quote_matches:
                print(f"   Quoted strings (potential starters):")
                for i, q in enumerate(quote_matches[:5]):
                    print(f"     {i+1}. {q}")

            # Find usage stats
            count_matches = re.findall(
                r"(\d+(?:\.\d+)?[KMk]?\+?)\s*(?:conversations?|chats?|uses?)",
                full_text,
                re.IGNORECASE,
            )
            if count_matches:
                print(f"   Usage stats: {count_matches}")

            # Screenshot
            print("\n7️⃣ Taking screenshot...")
            screenshot_path = f"debug_{gizmo_id}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"   Saved to: {screenshot_path}")

            # Save HTML
            print("\n8️⃣ Saving HTML...")
            html_path = f"debug_{gizmo_id}.html"
            content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   Saved to: {html_path}")

            # Keep browser open
            print("\n" + "=" * 70)
            print("✅ Browser will stay open for manual inspection")
            print("   Check the page to see what data should be extracted")
            input("\nPress Enter to close...")

        finally:
            await browser.close()


async def main():
    import sys

    if len(sys.argv) < 2:
        print(
            """
Debug GPT Metadata Extraction

Usage:
    python3 debug_extractor.py <gizmo_id>

Examples:
    # Debug a specific GPT
    python3 debug_extractor.py g-h8l4uLHFQ
    
    # Debug from your data
    python3 debug_extractor.py g-68d8ecbe98388191bd93f6b1d03158bf

This will:
1. Open the GPT page
2. Show what text/elements are found
3. Display extraction candidates
4. Save screenshot and HTML for inspection
5. Keep browser open for manual checking
        """
        )

        # Use default for demo
        print("\nUsing default GPT for demo...")
        gizmo_id = "g-h8l4uLHFQ"  # Video AI by invideo
    else:
        gizmo_id = sys.argv[1]

    await debug_single_gpt(gizmo_id)


if __name__ == "__main__":
    asyncio.run(main())
