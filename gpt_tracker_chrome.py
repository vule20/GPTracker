"""
gpt_tracker_dropdown.py
Created: 2025-11-16 17:07
Author: VuLe@UMass Amherst
Last updated: 2025-11-16 17:07
Last modified by: VuLe@UMass Amherst
License: © Copyright 2025, Vu Le
Desc:
"""

"""
GPTracker - Dropdown Extraction Method
The search results appear in a dropdown menu, not on the main page!

Features:
- Types into search box to trigger search
- Extracts GPTs from dropdown autocomplete menu
- Scrolls within dropdown (not main page)
- Clicks "See more" repeatedly to load all results
- Timeout mechanism: stops if no new results within 15 seconds
- Smart stopping: auto-detects when all results loaded
"""

import asyncio
import json
import csv
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import re

from playwright.async_api import async_playwright, Page, Browser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Experiment modes based on GPTracker paper replication
MODES = {
    "test": {
        "name": "Test Mode",
        "keywords": 10,
        "detail_limit": 20,
        "description": "Quick test (~5 minutes)",
    },
    "small": {
        "name": "Small Scale (Class Project)",
        "keywords": 500,
        "detail_limit": 2000,
        "description": "~2-4 hours, good for class projects",
    },
    "medium": {
        "name": "Medium Scale",
        "keywords": 1500,
        "detail_limit": 5000,
        "description": "~6-8 hours, better analysis",
    },
    "full": {
        "name": "Full Replication",
        "keywords": 10000,
        "detail_limit": 10000,
        "description": "~24+ hours, paper replication",
    },
}


def generate_keywords(num_keywords: int) -> List[str]:
    """
    Generate keywords for GPT search
    Based on common categories and topics
    """
    # Core categories from GPT store
    base_keywords = [
        # Programming & Tech
        "code",
        "python",
        "javascript",
        "programming",
        "developer",
        "debug",
        "API",
        "web development",
        "data science",
        "machine learning",
        "SQL",
        "database",
        "algorithm",
        "software",
        "app development",
        # Writing & Content
        "write",
        "writing",
        "content",
        "blog",
        "article",
        "essay",
        "copywriting",
        "creative writing",
        "story",
        "novel",
        "script",
        "email",
        "letter",
        "resume",
        "CV",
        "cover letter",
        # Business & Productivity
        "business",
        "marketing",
        "SEO",
        "sales",
        "strategy",
        "productivity",
        "planning",
        "project management",
        "analysis",
        "presentation",
        "report",
        "spreadsheet",
        "data analysis",
        # Education & Learning
        "tutor",
        "teacher",
        "learn",
        "study",
        "homework",
        "exam",
        "math",
        "science",
        "history",
        "language",
        "grammar",
        "explain",
        "education",
        "training",
        "course",
        # Creative & Design
        "design",
        "logo",
        "graphics",
        "image",
        "art",
        "creative",
        "video",
        "music",
        "audio",
        "animation",
        "illustration",
        "photo",
        "drawing",
        "sketch",
        "color",
        "style",
        # Research & Analysis
        "research",
        "analyze",
        "summarize",
        "review",
        "compare",
        "data",
        "statistics",
        "insights",
        "trends",
        "forecast",
        "academic",
        "paper",
        "citation",
        "reference",
        # Communication & Social
        "chat",
        "conversation",
        "assistant",
        "helper",
        "guide",
        "advice",
        "tips",
        "suggestions",
        "recommendations",
        "social media",
        "post",
        "caption",
        "hashtag",
        # Legal & Finance
        "legal",
        "law",
        "contract",
        "compliance",
        "policy",
        "finance",
        "investment",
        "budget",
        "tax",
        "accounting",
        "crypto",
        "stock",
        "trading",
        "money",
        "price",
        # Health & Wellness
        "health",
        "fitness",
        "workout",
        "diet",
        "nutrition",
        "mental health",
        "meditation",
        "therapy",
        "wellness",
        "medical",
        "doctor",
        "symptom",
        "diagnosis",
        # Entertainment & Fun
        "game",
        "quiz",
        "trivia",
        "puzzle",
        "riddle",
        "joke",
        "funny",
        "entertainment",
        "fun",
        "play",
        "movie",
        "book",
        "music",
        "tv show",
        "anime",
        # Specialized Tools
        "translate",
        "translation",
        "language",
        "dictionary",
        "calculator",
        "converter",
        "tool",
        "utility",
        "generator",
        "maker",
        "builder",
        "creator",
        # Niche & Specific
        "cooking",
        "recipe",
        "food",
        "travel",
        "destination",
        "fashion",
        "style",
        "beauty",
        "makeup",
        "skincare",
        "pet",
        "dog",
        "cat",
        "gardening",
        "plants",
        "car",
        "automotive",
        "real estate",
        "home",
        "DIY",
    ]

    # Extend with combinations and variations if needed
    extended_keywords = base_keywords.copy()

    # Add combinations for larger keyword sets
    if num_keywords > len(base_keywords):
        combinations = [
            "AI",
            "GPT",
            "ChatGPT",
            "expert",
            "professional",
            "advanced",
            "simple",
            "easy",
            "quick",
            "best",
            "free",
            "pro",
            "premium",
            "ultimate",
            "complete",
        ]

        for combo in combinations:
            for base in base_keywords[:50]:  # Top 50 base keywords
                extended_keywords.append(f"{combo} {base}")
                if len(extended_keywords) >= num_keywords:
                    break
            if len(extended_keywords) >= num_keywords:
                break

    return extended_keywords[:num_keywords]


class GPTrackerDropdown:
    """
    Crawler that extracts from the search dropdown
    The ACTUAL way ChatGPT shows search results!
    """

    def __init__(
        self,
        output_dir: str = "data",
        delay: float = 2.0,
        max_see_more_clicks: int = 20,
        result_timeout: float = 15.0,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.max_see_more_clicks = max_see_more_clicks
        self.result_timeout = result_timeout  # Timeout for waiting for new results
        self.gpts = {}
        self.round_date = datetime.now().strftime("%Y-%m-%d")
        self.stats = {"keywords_searched": 0, "gpts_discovered": 0, "gpts_detailed": 0}

    async def connect_to_chrome(self, playwright):
        """Connect to existing Chrome browser"""

        logger.info("🔌 Connecting to Chrome on port 9222...")

        try:
            browser = await playwright.chromium.connect_over_cdp(
                "http://localhost:9222"
            )

            contexts = browser.contexts
            if not contexts:
                logger.error("❌ No browser contexts found")
                return None, None

            context = contexts[0]
            page = await context.new_page()

            logger.info("✅ Connected!")

            # Verify login
            try:
                await page.goto("https://chatgpt.com/gpts", timeout=30000)
                await asyncio.sleep(2)

                content = await page.content()
                if "Sign up" in content or "Log in" in content:
                    logger.warning("⚠️  Not logged in!")
                else:
                    logger.info("✅ Logged in to ChatGPT")
            except Exception as e:
                logger.warning(f"Login check failed: {e}")

            return browser, page

        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return None, None

    async def extract_from_dropdown(self, page: Page) -> List[Dict]:
        """
        Extract GPTs from the dropdown menu
        The dropdown contains <li> elements with IDs like: _r_1a_g-{gizmo_id}
        """
        try:
            gpts = await page.evaluate(
                """
                () => {
                    const gpts = [];
                    const seen = new Set();
                    
                    // Find all list items in the dropdown
                    // They have IDs like "_r_1a_g-67b80abc268c8191b767ae1920687254"
                    const listItems = document.querySelectorAll('li[id*="_g-"]');
                    
                    listItems.forEach(li => {
                        const id = li.getAttribute('id');
                        
                        // Skip the load-more button
                        if (id.includes('load-more')) {
                            return;
                        }
                        
                        // Extract gizmo ID from the li ID
                        // Pattern: _r_1a_g-{gizmo_id} or similar
                        const match = id.match(/(g-[a-zA-Z0-9]+)/);
                        
                        if (match) {
                            const gizmoId = match[1];
                            
                            if (!seen.has(gizmoId)) {
                                seen.add(gizmoId);
                                
                                // Extract GPT details from the dropdown item
                                const nameElem = li.querySelector('.font-semibold, .text-sm.font-semibold');
                                
                                // Extract profile image URL
                                const imgElem = li.querySelector('img[alt="GPT Icon"]');
                                const profileImageUrl = imgElem ? imgElem.src : null;
                                
                                // Extract conversation count
                                // It's in a span after the conversation icon
                                const convElems = li.querySelectorAll('.flex.items-center.gap-1 span');
                                let convCount = null;
                                for (const elem of convElems) {
                                    const text = elem.innerText.trim();
                                    // Look for patterns like "10M+", "1M+", "100K+", etc.
                                    if (text.match(/[\d.]+[KMB]?\+?/)) {
                                        convCount = text;
                                        break;
                                    }
                                }
                                
                                // Extract author (it's in a div with class text-token-text-tertiary truncate text-xs)
                                const authorElems = li.querySelectorAll('.text-token-text-tertiary.truncate.text-xs');
                                let author = null;
                                for (const elem of authorElems) {
                                    const text = elem.innerText.trim();
                                    if (text.startsWith('By ')) {
                                        author = text.replace('By ', '');
                                        break;
                                    }
                                }
                                
                                gpts.push({
                                    gizmo_id: gizmoId,
                                    name: nameElem ? nameElem.innerText.trim() : null,
                                    author: author,
                                    conversations: convCount,
                                    profile_image_url: profileImageUrl
                                });
                            }
                        }
                    });
                    
                    return gpts;
                }
            """
            )

            return gpts

        except Exception as e:
            logger.error(f"Error extracting from dropdown: {e}")
            return []

    async def click_see_more(self, page: Page) -> bool:
        """
        Click the 'See more' button in the dropdown to load more results
        Returns True if button was found and clicked, False otherwise
        """
        try:
            # Wait for and click the "See more" button
            # It's specifically in the dropdown with id containing "load-more-button"
            see_more_selectors = [
                'li[id*="load-more-button"] button',
                'li[id*="load-more"] button',
                'ul[role="listbox"] button:has-text("See more")',
                'div[role="dialog"] button:has-text("See more")',
            ]

            see_more = None
            for selector in see_more_selectors:
                try:
                    see_more = await page.wait_for_selector(
                        selector, timeout=2000, state="visible"
                    )
                    if see_more:
                        break
                except:
                    continue

            if see_more:
                # Check if button is visible
                is_visible = await see_more.is_visible()
                if not is_visible:
                    logger.debug(f"  'See more' button not visible")
                    return False

                logger.info("  🔽 Clicking 'See more'...")
                await see_more.click()
                await asyncio.sleep(1)  # Wait for more results to load
                return True
            else:
                return False

        except Exception as e:
            logger.debug(f"  'See more' error: {e}")
            return False

    async def search_dropdown(self, page: Page, keyword: str) -> List[Dict]:
        """
        Search by typing and extracting from dropdown
        """
        gpts = []

        try:
            logger.info(f"  🔍 Searching for '{keyword}'...")

            # Go to GPT store
            await page.goto(
                "https://chatgpt.com/gpts", wait_until="domcontentloaded", timeout=30000
            )
            await asyncio.sleep(1.5)

            # Find search box
            search_box = None
            selectors = [
                'input[id="search"]',
                'input[aria-label="Search GPTs"]',
                'input[placeholder*="Search"]',
            ]

            for selector in selectors:
                try:
                    search_box = await page.wait_for_selector(selector, timeout=5000)
                    if search_box:
                        logger.info(f"  ✅ Found search box")
                        break
                except:
                    continue

            if not search_box:
                logger.error("  ❌ Could not find search box!")
                return []

            # Clear and type
            await search_box.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")

            logger.info(f"  ⌨️  Typing '{keyword}'...")
            await search_box.type(keyword, delay=50)

            # Wait for dropdown to appear
            logger.info(f"  ⏳ Waiting for dropdown...")
            await asyncio.sleep(self.delay)

            # Wait for dropdown container and list items
            try:
                # The dropdown is in a div with role="dialog"
                await page.wait_for_selector('div[role="dialog"]', timeout=10000)
                await page.wait_for_selector('li[id*="_g-"]', timeout=10000)
                logger.info(f"  ✅ Dropdown appeared!")
            except:
                logger.warning(f"  ⚠️  Dropdown didn't appear")

            # Extract initial results
            initial_gpts = await self.extract_from_dropdown(page)
            logger.info(f"  📊 Initial: {len(initial_gpts)} GPTs in dropdown")

            # Keep clicking "See more" until no more results
            max_clicks = self.max_see_more_clicks  # Configurable limit
            click_count = 0
            previous_count = len(initial_gpts)

            logger.info(f"  🔄 Loading all results (max {max_clicks} clicks)...")

            while click_count < max_clicks:
                # Scroll within the dropdown to reveal "See more" button
                try:
                    await page.evaluate(
                        """
                        () => {
                            const listbox = document.querySelector('ul[role="listbox"]');
                            if (listbox) {
                                listbox.scrollTop = listbox.scrollHeight;
                            }
                        }
                    """
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"  Dropdown scroll error: {e}")

                # Try to click "See more"
                clicked = await self.click_see_more(page)

                if not clicked:
                    logger.info(f"  ✓ No more 'See more' button")
                    break

                click_count += 1

                # Wait for new results with timeout
                logger.debug(
                    f"  ⏳ Waiting for new results (timeout: {self.result_timeout}s)..."
                )
                start_time = asyncio.get_event_loop().time()
                timeout_reached = False
                new_results_loaded = False

                # Poll for new results with timeout
                while (
                    asyncio.get_event_loop().time() - start_time
                ) < self.result_timeout:
                    await asyncio.sleep(0.5)  # Check every 0.5 seconds

                    # Extract current GPTs
                    current_gpts = await self.extract_from_dropdown(page)
                    current_count = len(current_gpts)

                    # Check if we got new results
                    if current_count > previous_count:
                        new_results_loaded = True
                        new_gpts = current_count - previous_count
                        logger.info(
                            f"  📊 Click {click_count}/{max_clicks}: {current_count} total (+{new_gpts} new)"
                        )
                        previous_count = current_count
                        break  # Exit polling loop, continue to next "See more" click

                # Check if timeout was reached without new results
                if not new_results_loaded:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info(
                        f"  ⏱️  Timeout after {elapsed:.1f}s - no new results loaded"
                    )
                    logger.info(f"  ✓ Reached end of results")
                    break  # Exit main loop

            # Final extraction
            gpts_data = await self.extract_from_dropdown(page)
            logger.info(f"  ✅ Final: {len(gpts_data)} GPTs loaded from dropdown")

            # Convert to our format
            for gpt_data in gpts_data:
                gpts.append(
                    {
                        "gizmo_id": gpt_data["gizmo_id"],
                        "from": "search",
                        "url": f"https://chatgpt.com/g/{gpt_data['gizmo_id']}",
                        "found_with_keyword": keyword,
                        "gizmo": {
                            "display": {
                                "name": gpt_data.get("name"),
                                "profile_image_url": gpt_data.get("profile_image_url"),
                            },
                            "author": {"display_name": gpt_data.get("author")},
                            "vanity_metrics": {
                                "num_conversations_str": gpt_data.get("conversations")
                            },
                        },
                    }
                )

            # Debug if no results
            if len(gpts) == 0:
                logger.warning(f"  ⚠️  No GPTs found for '{keyword}'")

                try:
                    await page.screenshot(path=f"debug_{keyword}.png", full_page=True)
                    logger.info(f"  📸 Screenshot: debug_{keyword}.png")

                    html = await page.content()
                    with open(f"debug_{keyword}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.info(f"  💾 HTML: debug_{keyword}.html")
                except Exception as e:
                    logger.warning(f"  Debug save error: {e}")
            else:
                logger.info(f"  ✅ '{keyword}': Found {len(gpts)} GPTs")

            self.stats["keywords_searched"] += 1

        except Exception as e:
            logger.error(f"  ❌ Error searching '{keyword}': {e}")
            import traceback

            traceback.print_exc()

        return gpts

    async def get_gpt_details(self, page: Page, gizmo_id: str, url: str) -> Dict:
        """Extract detailed metadata from GPT page"""
        details = {
            "gizmo": {
                "id": gizmo_id,
                "display": {
                    "name": None,
                    "description": None,
                    "prompt_starters": [],
                    "categories": [],
                },
                "author": {"display_name": None},
                "vanity_metrics": {
                    "rating": None,
                    "num_conversations_str": None,
                    "rank": None,
                },
            },
            "tools": [],
            "status": "unknown",
        }

        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)

            if response and response.status == 404:
                details["status"] = "unavailable"
                return details

            await asyncio.sleep(3)

            full_text = await page.evaluate("() => document.body.innerText")
            content = await page.content()

            if "not found" in content.lower():
                details["status"] = "unavailable"
                return details

            details["status"] = "available"

            # Extract name
            name_elem = await page.query_selector("div.text-2xl.font-semibold")
            if name_elem:
                name = await name_elem.text_content()
                if name:
                    details["gizmo"]["display"]["name"] = name.strip()

            # Extract description
            desc_match = re.search(r"[\d\.]+\s*[★⭐]\s*-\s*(.+?)(?:\n|$)", full_text)
            if desc_match:
                details["gizmo"]["display"]["description"] = desc_match.group(1).strip()

            # Extract author
            author_elem = await page.query_selector(
                "div.text-sm.text-token-text-tertiary"
            )
            if author_elem:
                author_text = await author_elem.text_content()
                if author_text:
                    author_match = re.search(r"By (.+)", author_text)
                    if author_match:
                        details["gizmo"]["author"]["display_name"] = author_match.group(
                            1
                        ).strip()

            # Extract rating
            rating_match = re.search(r"(\d+\.\d+)\s*[★⭐]", full_text)
            if rating_match:
                details["gizmo"]["vanity_metrics"]["rating"] = float(
                    rating_match.group(1)
                )

            # Extract conversations
            conv_match = re.search(
                r"([\d\.]+[KMB]?\+?)\s+Conversations?", full_text, re.IGNORECASE
            )
            if conv_match:
                details["gizmo"]["vanity_metrics"]["num_conversations_str"] = (
                    conv_match.group(1)
                )

            self.stats["gpts_detailed"] += 1

        except Exception as e:
            logger.warning(f"Error getting details for {gizmo_id}: {e}")

        return details

    async def crawl(
        self, keywords: List[str], fetch_details: bool = True, detail_limit: int = None
    ):
        """Main crawl process"""
        logger.info(f"🚀 Starting GPTracker (Dropdown Method) - {self.round_date}")

        async with async_playwright() as p:
            browser, page = await self.connect_to_chrome(p)

            if not browser or not page:
                logger.error("❌ Could not connect to Chrome")
                return

            try:
                # Phase 1: Search
                logger.info(f"\n📍 Phase 1: Searching with {len(keywords)} keywords\n")

                for i, keyword in enumerate(keywords, 1):
                    gpts = await self.search_dropdown(page, keyword)

                    for gpt in gpts:
                        gizmo_id = gpt["gizmo_id"]
                        if gizmo_id not in self.gpts:
                            self.gpts[gizmo_id] = gpt
                            self.stats["gpts_discovered"] += 1

                logger.info(
                    f"\n✓ Phase 1 complete: {len(self.gpts)} unique GPTs discovered"
                )

                # Phase 2: Details
                if fetch_details and len(self.gpts) > 0:
                    gpt_ids = list(self.gpts.keys())
                    if detail_limit:
                        gpt_ids = gpt_ids[:detail_limit]

                    logger.info(
                        f"\n📍 Phase 2: Fetching details for {len(gpt_ids)} GPTs\n"
                    )

                    for i, gizmo_id in enumerate(gpt_ids, 1):
                        if i % 10 == 0:
                            logger.info(f"  Progress: {i}/{len(gpt_ids)}")

                        gpt = self.gpts[gizmo_id]
                        details = await self.get_gpt_details(page, gizmo_id, gpt["url"])
                        self.gpts[gizmo_id].update(details)

                    logger.info(
                        f"✓ Phase 2 complete: {self.stats['gpts_detailed']} detailed"
                    )

                if len(self.gpts) > 0:
                    await self.save_results()
                else:
                    logger.warning("⚠️  No GPTs found")

            except Exception as e:
                logger.error(f"Error during crawl: {e}")
                import traceback

                traceback.print_exc()

            finally:
                logger.info("\n✅ Done!")

        self.print_summary()

    async def save_results(self):
        """Save results"""
        csv_file = self.output_dir / f"all_{self.round_date}.csv"

        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["gizmo_id", "from", "json", "status", "round"]
            )
            writer.writeheader()

            for gizmo_id, gpt_data in self.gpts.items():
                writer.writerow(
                    {
                        "gizmo_id": gizmo_id,
                        "from": gpt_data.get("from", "search"),
                        "json": json.dumps(gpt_data, ensure_ascii=False),
                        "status": gpt_data.get("status", "available"),
                        "round": self.round_date,
                    }
                )

        logger.info(f"✓ Saved: {csv_file}")

        json_file = self.output_dir / f"all_{self.round_date}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(list(self.gpts.values()), f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved: {json_file}")

    def print_summary(self):
        """Print summary"""
        logger.info("\n" + "=" * 60)
        logger.info("CRAWL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Keywords: {self.stats['keywords_searched']}")
        logger.info(f"GPTs Found: {self.stats['gpts_discovered']}")
        logger.info(f"Detailed: {self.stats['gpts_detailed']}")
        logger.info("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="GPTracker - GPT Store Scraper for Misuse Detection Research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  --test      Quick test (10 keywords, 20 detailed GPTs)
              ~5 minutes, good for testing setup
  
  --small     Class project scale (500 keywords, 2K GPTs)
              ~2-4 hours, recommended for class projects
  
  --medium    Good coverage (1500 keywords, 5K GPTs)
              ~6-8 hours, better for analysis
  
  --full      Paper replication (10K keywords, 10K GPTs)
              ~24+ hours, full replication attempt

EXAMPLES:
  python gpt_tracker_dropdown.py --test
  python gpt_tracker_dropdown.py --small
  python gpt_tracker_dropdown.py --full --no-details
        """,
    )

    parser.add_argument(
        "--test", action="store_true", help="Test mode (10 keywords, 20 GPTs, ~5 min)"
    )
    parser.add_argument(
        "--small",
        action="store_true",
        help="Small scale (500 keywords, 2K GPTs, ~2-4 hours)",
    )
    parser.add_argument(
        "--medium",
        action="store_true",
        help="Medium scale (1500 keywords, 5K GPTs, ~6-8 hours)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full replication (10K keywords, 10K GPTs, ~24+ hours)",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching detailed GPT info (faster)",
    )
    parser.add_argument(
        "--keywords", type=int, help="Custom number of keywords (overrides mode)"
    )
    parser.add_argument(
        "--detail-limit", type=int, help="Custom detail limit (overrides mode)"
    )

    args = parser.parse_args()

    # Determine mode
    if args.test:
        mode = "test"
    elif args.small:
        mode = "small"
    elif args.medium:
        mode = "medium"
    elif args.full:
        mode = "full"
    else:
        # Default to test mode if no mode specified
        mode = "test"
        logger.info("No mode specified, using --test mode")

    config = MODES[mode]
    num_keywords = args.keywords if args.keywords else config["keywords"]
    detail_limit = args.detail_limit if args.detail_limit else config["detail_limit"]
    fetch_details = not args.no_details

    print(
        f"""
╔══════════════════════════════════════════════════════════════════╗
║     GPTracker - GPT Store Scraper (Dropdown Extraction)         ║
║     For: S&P'25 GPTracker Paper Replication                     ║
╚══════════════════════════════════════════════════════════════════╝

MODE: {config['name']}
- Keywords: {num_keywords}
- Detail limit: {detail_limit}
- Fetch details: {fetch_details}
- Estimated time: {config['description']}

✅ Extracts from dropdown (CORRECT METHOD)
✅ Multi-click "See more" (up to 20 times)
✅ 15-second timeout per click
✅ Profile image URLs for impersonation detection
✅ Conversation counts for popularity metrics

SETUP:
  1. Chrome with --remote-debugging-port=9222
  2. Logged into ChatGPT
  3. Run this script
    """
    )

    await asyncio.sleep(2)

    keywords = generate_keywords(num_keywords)
    logger.info(f"Generated {len(keywords)} keywords")

    crawler = GPTrackerDropdown(
        output_dir=f"data/{mode}",
        delay=2.0,
        max_see_more_clicks=20,
        result_timeout=15.0,
    )
    await crawler.crawl(
        keywords, fetch_details=fetch_details, detail_limit=detail_limit
    )


if __name__ == "__main__":
    asyncio.run(main())
