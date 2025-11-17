# enhance_gpt_data.py
# Created on: 2025-11-17 02:07:10
# Author: VuLe@macbook
# Last updated: 2025-11-17 02:08:07
# Last modified by: VuLe@macbook

"""
enhance_gpt_data.py

This script reads your original scraper's output and enhances it by visiting each GPT page.

Workflow:
1. Your original script runs → creates JSON with basic data
2. This script reads that JSON
3. Visits each GPT URL one by one
4. Scrapes: description, prompt_starters, rating, capabilities
5. Updates the JSON file

Usage:
    python enhance_gpt_data.py --input data/test/all_2025-11-16.json --limit 20
"""

import asyncio
import json
import logging
import argparse
import re
from pathlib import Path
from typing import Dict, List

from playwright.async_api import async_playwright, Page

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GPTPageScraper:
    """Scrapes GPT pages to get complete data"""
    
    def __init__(self):
        pass
    
    async def connect_to_chrome(self, p):
        """Connect to existing Chrome instance"""
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            contexts = browser.contexts
            if not contexts:
                logger.error("No browser contexts found")
                return None, None
            
            context = contexts[0]
            pages = context.pages
            if not pages:
                page = await context.new_page()
            else:
                page = pages[0]
            
            logger.info("✓ Connected to Chrome")
            return browser, page
        
        except Exception as e:
            logger.error(f"Failed to connect to Chrome: {e}")
            return None, None
    
    async def scrape_gpt_page(self, page: Page, gpt_url: str) -> Dict:
        """
        Visit a GPT's full page and scrape all data.
        
        Extracts from the page HTML:
        - description
        - prompt_starters (conversation starters)
        - rating
        - rating_count
        - category_ranking
        - capabilities
        - conversations
        """
        details = {
            "description": None,
            "prompt_starters": [],
            "rating": None,
            "rating_count": None,
            "category_ranking": None,
            "num_conversations_str": None,
            "capabilities": [],
            "status": "unknown",
        }
        
        try:
            # Navigate to GPT page
            response = await page.goto(gpt_url, wait_until="domcontentloaded", timeout=30000)
            
            if response and response.status == 404:
                details["status"] = "unavailable"
                return details
            
            await asyncio.sleep(2)
            
            # Get page text and HTML
            page_text = await page.evaluate("() => document.body.innerText")
            page_html = await page.content()
            
            if "not found" in page_html.lower():
                details["status"] = "unavailable"
                return details
            
            details["status"] = "available"
            
            # Extract description
            # It's in a div with class like "text-center text-sm font-normal"
            try:
                desc_elem = await page.query_selector(".text-center.text-sm.font-normal")
                if desc_elem:
                    desc = await desc_elem.text_content()
                    if desc and desc.strip():
                        details["description"] = desc.strip()
            except:
                pass
            
            # If description not found, try from text
            if not details["description"]:
                desc_match = re.search(r"By [^\n]+\n+([^\n]+)", page_text)
                if desc_match:
                    desc = desc_match.group(1).strip()
                    if len(desc) > 20 and len(desc) < 300:
                        details["description"] = desc
            
            # Extract conversation starters
            # They're in buttons with text like "/start Python", "/canvas document"
            try:
                starter_buttons = await page.query_selector_all("button .line-clamp-3")
                starters = []
                for btn in starter_buttons[:4]:  # Limit to 4
                    text = await btn.text_content()
                    if text and text.strip() and text.strip().startswith('/'):
                        starters.append(text.strip())
                
                if starters:
                    details["prompt_starters"] = starters
            except:
                pass
            
            # If no starters found with slash, try general conversation starters
            if not details["prompt_starters"]:
                try:
                    starter_buttons = await page.query_selector_all("button .break-word")
                    starters = []
                    for btn in starter_buttons[:4]:
                        text = await btn.text_content()
                        if text and text.strip() and len(text.strip()) > 5:
                            starters.append(text.strip())
                    
                    if starters:
                        details["prompt_starters"] = starters[:4]
                except:
                    pass
            
            # Extract rating (e.g., "4.1")
            rating_match = re.search(r"([\d\.]+)\s*Ratings", page_text)
            if rating_match:
                try:
                    details["rating"] = float(rating_match.group(1))
                except:
                    pass
            
            # Extract rating count (e.g., "25K+")
            rating_count_match = re.search(r"Ratings\s*\(([^)]+)\)", page_text)
            if rating_count_match:
                details["rating_count"] = rating_count_match.group(1)
            
            # Extract category ranking (e.g., "#2 in Programming")
            ranking_match = re.search(r"(#\d+)\s+in\s+([^\n]+)", page_text)
            if ranking_match:
                details["category_ranking"] = f"{ranking_match.group(1)} in {ranking_match.group(2).strip()}"
            
            # Extract conversation count
            conv_match = re.search(r"([\d\.]+[KMB]?\+?)\s+Conversations?", page_text, re.IGNORECASE)
            if conv_match:
                details["num_conversations_str"] = conv_match.group(1)
            
            # Extract capabilities
            capabilities = []
            if "Code Interpreter" in page_text or "Data Analysis" in page_text:
                capabilities.append("code_interpreter")
            if "Web Search" in page_text or "Web Browsing" in page_text:
                capabilities.append("web_search")
            if "DALL" in page_text or "Image" in page_text:
                capabilities.append("dalle")
            if "Canvas" in page_text:
                capabilities.append("canvas")
            details["capabilities"] = capabilities
            
        except Exception as e:
            logger.debug(f"Error scraping page: {e}")
            details["status"] = "error"
        
        return details
    
    async def enhance_json_file(self, input_file: str, output_file: str = None, limit: int = None):
        """
        Read JSON from your original script and enhance with page scraping.
        
        Args:
            input_file: JSON file from your original script
            output_file: Output file (default: input_file with _enhanced suffix)
            limit: Limit number of GPTs to process (for testing)
        """
        # Read input JSON
        logger.info(f"Loading: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            gpts = json.load(f)
        
        logger.info(f"Found {len(gpts)} GPTs")
        
        # Filter available GPTs
        available_gpts = [g for g in gpts if g.get('status') == 'available']
        logger.info(f"Available GPTs: {len(available_gpts)}")
        
        if limit:
            available_gpts = available_gpts[:limit]
            logger.info(f"Limiting to {limit} GPTs")
        
        # Connect to Chrome
        async with async_playwright() as p:
            browser, page = await self.connect_to_chrome(p)
            
            if not browser or not page:
                logger.error("❌ Could not connect to Chrome")
                return
            
            try:
                enhanced_gpts = []
                
                # Process each GPT
                for idx, gpt in enumerate(gpts, 1):
                    # Skip if not in our available list
                    if gpt not in available_gpts:
                        enhanced_gpts.append(gpt)
                        continue
                    
                    gpt_url = gpt.get('url', '')
                    gizmo_id = gpt.get('gizmo_id', '?')
                    
                    logger.info(f"[{idx}/{len(gpts)}] Scraping: {gizmo_id}")
                    
                    # Scrape the page
                    page_data = await self.scrape_gpt_page(page, gpt_url)
                    
                    # Update GPT data
                    enhanced_gpt = {**gpt}  # Copy original
                    
                    # Update with scraped data
                    if page_data["status"] == "available":
                        if page_data["description"]:
                            enhanced_gpt["gizmo"]["display"]["description"] = page_data["description"]
                        
                        if page_data["prompt_starters"]:
                            enhanced_gpt["gizmo"]["display"]["prompt_starters"] = page_data["prompt_starters"]
                        
                        if page_data["rating"] is not None:
                            enhanced_gpt["gizmo"]["vanity_metrics"]["rating"] = page_data["rating"]
                        
                        if page_data["rating_count"]:
                            enhanced_gpt["gizmo"]["vanity_metrics"]["rating_count"] = page_data["rating_count"]
                        
                        if page_data["category_ranking"]:
                            enhanced_gpt["gizmo"]["vanity_metrics"]["rank"] = page_data["category_ranking"]
                        
                        if page_data["num_conversations_str"]:
                            enhanced_gpt["gizmo"]["vanity_metrics"]["num_conversations_str"] = page_data["num_conversations_str"]
                        
                        enhanced_gpt["gizmo"]["capabilities"] = page_data["capabilities"]
                    
                    enhanced_gpts.append(enhanced_gpt)
                    
                    # Save progress every 10 GPTs
                    if idx % 10 == 0:
                        logger.info(f"  Saving progress...")
                        output_path = output_file or input_file.replace('.json', '_enhanced.json')
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(enhanced_gpts, f, indent=2, ensure_ascii=False)
                    
                    # Small delay between requests
                    await asyncio.sleep(0.5)
                
                # Final save
                output_path = output_file or input_file.replace('.json', '_enhanced.json')
                logger.info(f"Saving to: {output_path}")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_gpts, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✓ Enhanced {len(available_gpts)} GPTs")
                
                # Show summary
                with_desc = sum(1 for g in enhanced_gpts if g.get('gizmo', {}).get('display', {}).get('description'))
                with_starters = sum(1 for g in enhanced_gpts if len(g.get('gizmo', {}).get('display', {}).get('prompt_starters', [])) > 0)
                with_rating = sum(1 for g in enhanced_gpts if g.get('gizmo', {}).get('vanity_metrics', {}).get('rating') is not None)
                
                logger.info(f"\nSummary:")
                logger.info(f"  With description: {with_desc}")
                logger.info(f"  With prompt_starters: {with_starters}")
                logger.info(f"  With rating: {with_rating}")
                
            except Exception as e:
                logger.error(f"Error during enhancement: {e}")
                import traceback
                traceback.print_exc()


async def main():
    parser = argparse.ArgumentParser(
        description="Enhance GPT data by visiting each page",
        epilog="""
WORKFLOW:
  Step 1: Run your original script
          python gpt_tracker_chrome.py --test
          Output: data/test/all_20251117.json
  
  Step 2: Run this enhancement script
          python enhance_gpt_data.py --input data/test/all_20251117.json
          Output: data/test/all_20251117_enhanced.json

EXAMPLES:
  # Enhance all GPTs
  python enhance_gpt_data.py --input data/test/all_20251117.json
  
  # Test with first 20 GPTs
  python enhance_gpt_data.py --input data/test/all_20251117.json --limit 20
  
  # Specify output file
  python enhance_gpt_data.py --input data/test/all_20251117.json --output complete_data.json
        """
    )
    
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file from your original script"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file (default: input_file_enhanced.json)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of GPTs to process (for testing)"
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        return
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║     GPT Data Enhancer - Page Scraper                            ║
║     Visits each GPT page to get complete data                   ║
╚══════════════════════════════════════════════════════════════════╝

Input:  {args.input}
Output: {args.output or args.input.replace('.json', '_enhanced.json')}
Limit:  {args.limit if args.limit else 'All GPTs'}

✅ Reads your original scraper's JSON
✅ Visits each GPT's full page
✅ Extracts: description, prompt_starters, rating, capabilities
✅ Updates JSON with complete data

SETUP:
  1. Chrome with --remote-debugging-port=9222 (already running)
  2. Logged into ChatGPT
  3. Run this script
    """)
    
    await asyncio.sleep(2)
    
    scraper = GPTPageScraper()
    await scraper.enhance_json_file(args.input, args.output, limit=args.limit)
    
    output_path = args.output or args.input.replace('.json', '_enhanced.json')
    print(f"\n✅ Done! Enhanced data saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
