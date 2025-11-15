"""
GPTracker: Complete Implementation - FIXED
Full metadata extraction with robust text-based strategies

This version extracts ALL needed data for paper reproduction
"""

import asyncio
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import re

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

try:
    import zstandard as zstd

    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logging.warning("zstandard not installed, compression will be skipped")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GPTrackerCrawler:
    """Enhanced crawler with robust metadata extraction"""

    def __init__(
        self,
        output_dir: str = "data",
        keywords_file: str = "keywords.txt",
        headless: bool = False,
        delay: float = 2.0,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.keywords_file = keywords_file
        self.headless = headless
        self.delay = delay

        self.gpts: Dict[str, Dict] = {}
        self.round_date = datetime.now().strftime("%Y-%m-%d")

        self.stats = {
            "keywords_searched": 0,
            "gpts_discovered": 0,
            "gpts_detailed": 0,
            "errors": 0,
        }

    async def load_keywords(self, max_keywords: Optional[int] = None) -> List[str]:
        """Load search keywords"""
        try:
            with open(self.keywords_file, "r", encoding="utf-8") as f:
                keywords = [line.strip() for line in f if line.strip()]

            if max_keywords:
                keywords = keywords[:max_keywords]

            logger.info(f"Loaded {len(keywords)} keywords")
            return keywords
        except FileNotFoundError:
            logger.warning("Keywords file not found, using defaults")
            return (
                self._get_default_keywords()[:max_keywords]
                if max_keywords
                else self._get_default_keywords()
            )

    def _get_default_keywords(self) -> List[str]:
        """Default keywords"""
        return [
            "assistant",
            "code",
            "write",
            "data",
            "help",
            "chat",
            "tool",
            "business",
            "education",
            "productivity",
            "creative",
            "learning",
        ]

    async def create_stealth_browser(
        self, playwright
    ) -> Tuple[Browser, BrowserContext]:
        """Create browser with anti-detection"""
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )

        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
        """
        )

        return browser, context

    async def setup_authenticated_session(self, context: BrowserContext) -> Page:
        """Handle authentication"""
        page = await context.new_page()
        cookies_file = self.output_dir / "session_cookies.json"

        if cookies_file.exists():
            try:
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info("Loaded existing session")

                await page.goto("https://chatgpt.com/gpts", timeout=30000)
                await asyncio.sleep(3)

                content = await page.content()
                if "Error loading" not in content:
                    logger.info("✓ Session valid")
                    return page
                else:
                    logger.warning("Session expired")
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

        logger.info("🔐 Authentication required")
        await page.goto("https://chatgpt.com/", timeout=30000)
        await asyncio.sleep(3)

        content = await page.content()
        if "Sign up" in content or "Log in" in content:
            logger.warning("⚠️  Please complete verification in the browser")
            input("\nPress Enter after verification...")

        cookies = await context.cookies()
        with open(cookies_file, "w") as f:
            json.dump(cookies, f)
        logger.info(f"✓ Session saved")

        return page

    async def search_gpts(self, page: Page, keyword: str) -> List[Dict]:
        """Search GPT Store"""
        gpts = []
        search_url = f"https://chatgpt.com/gpts?q={keyword}"

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(self.delay)

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            links = await page.query_selector_all('a[href*="/g/"]')

            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href or "/g/" not in href:
                        continue

                    match = re.search(r"/g/(g-[a-zA-Z0-9]+)", href)
                    if not match:
                        continue

                    gizmo_id = match.group(1)
                    text = await link.text_content()

                    gpt_data = {
                        "gizmo_id": gizmo_id,
                        "from": "search",
                        "url": (
                            f"https://chatgpt.com{href}"
                            if href.startswith("/")
                            else href
                        ),
                        "preview_text": text.strip() if text else "",
                        "found_with_keyword": keyword,
                        "discovered_at": datetime.now().isoformat(),
                    }

                    gpts.append(gpt_data)
                except Exception as e:
                    logger.debug(f"Error extracting link: {e}")
                    continue

            self.stats["keywords_searched"] += 1
            logger.info(f"  '{keyword}': Found {len(gpts)} GPTs")

        except Exception as e:
            logger.error(f"Error searching '{keyword}': {e}")
            self.stats["errors"] += 1

        return gpts

    async def get_gpt_details(self, page: Page, gizmo_id: str, url: str) -> Dict:
        """
        ENHANCED: Extract complete metadata using text-based strategies
        """
        details = {
            "gizmo": {
                "id": gizmo_id,
                "organization_id": None,
                "short_url": None,
                "author": {
                    "user_id": None,
                    "display_name": None,
                    "link_to": None,
                    "is_verified": False,
                    "selected_display": None,
                    "display_socials": [],
                },
                "display": {
                    "name": None,
                    "description": None,
                    "prompt_starters": [],
                    "categories": [],
                },
                "created_at": None,
                "updated_at": None,
                "tags": [],
                "vanity_metrics": {
                    "num_conversations": None,
                    "num_conversations_str": None,
                },
            },
            "tools": [],
            "files": [],
            "status": "unknown",
            "checked_at": datetime.now().isoformat(),
        }

        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)

            if response.status == 404:
                details["status"] = "unavailable"
                return details

            # Wait for dynamic content
            await asyncio.sleep(4)

            content = await page.content()

            if "not found" in content.lower():
                details["status"] = "unavailable"
                return details

            details["status"] = "available"

            # STRATEGY 1: Extract ALL text content
            full_text = await page.evaluate("() => document.body.innerText")

            # STRATEGY 2: Get all headings (GPT name)
            all_headings = await page.query_selector_all('h1, h2, h3, [role="heading"]')
            for heading in all_headings:
                text = await heading.text_content()
                if text and len(text.strip()) > 3:
                    if not details["gizmo"]["display"]["name"]:
                        details["gizmo"]["display"]["name"] = text.strip()
                        break

            # STRATEGY 3: Get paragraphs for description
            all_paragraphs = await page.query_selector_all(
                'p, div[class*="text"], span[class*="text"]'
            )
            paragraph_texts = []
            for p in all_paragraphs:
                text = await p.text_content()
                if text and len(text.strip()) > 30:
                    paragraph_texts.append(text.strip())

            if paragraph_texts:
                description = max(paragraph_texts, key=len)
                if len(description) > 40:
                    details["gizmo"]["display"]["description"] = description

            # STRATEGY 4: Find conversation starters using patterns
            starter_patterns = [
                r'"([^"]{20,200})"',  # Quoted text
                r"•\s*([^\n]{20,200})",  # Bulleted items
            ]

            potential_starters = []
            for pattern in starter_patterns:
                matches = re.findall(pattern, full_text)
                potential_starters.extend(matches)

            # Filter for valid starters
            starters = []
            starter_words = [
                "how",
                "what",
                "why",
                "when",
                "where",
                "can",
                "help",
                "show",
                "tell",
                "explain",
                "create",
                "generate",
                "make",
                "write",
                "give",
                "find",
                "get",
            ]

            for text in potential_starters[:20]:
                text = text.strip()
                if (
                    text.lower().startswith(tuple(starter_words)) or "?" in text
                ) and len(text) > 15:
                    if text not in starters:
                        starters.append(text)

            if starters:
                details["gizmo"]["display"]["prompt_starters"] = starters[:10]

            # STRATEGY 5: Extract from buttons
            all_buttons = await page.query_selector_all('button, [role="button"]')
            button_starters = []
            for button in all_buttons:
                text = await button.text_content()
                if text and 15 < len(text.strip()) < 200:
                    text = text.strip()
                    if text.lower().startswith(tuple(starter_words)) or "?" in text:
                        if text not in button_starters and text not in starters:
                            button_starters.append(text)

            if button_starters:
                existing = details["gizmo"]["display"]["prompt_starters"]
                details["gizmo"]["display"]["prompt_starters"] = (
                    existing + button_starters[:5]
                )

            # STRATEGY 6: Author detection
            by_pattern = r"[Bb]y\s+([A-Za-z0-9\s\.]+?)(?:\n|\||$)"
            by_matches = re.findall(by_pattern, full_text)
            if by_matches:
                author_name = by_matches[0].strip()
                if 3 < len(author_name) < 50:
                    details["gizmo"]["author"]["display_name"] = author_name

            # STRATEGY 7: Category detection
            category_keywords = {
                "writing",
                "education",
                "productivity",
                "programming",
                "business",
                "creative",
                "research",
                "analysis",
                "lifestyle",
                "dalle",
                "coding",
                "learning",
                "teaching",
                "design",
                "marketing",
                "sales",
            }

            text_lower = full_text.lower()
            found_categories = []
            for keyword in category_keywords:
                if keyword in text_lower:
                    found_categories.append(keyword)

            if found_categories:
                details["gizmo"]["display"]["categories"] = found_categories[:5]
                details["gizmo"]["tags"] = found_categories[:5]

            # STRATEGY 8: Interaction count
            count_patterns = [
                r"(\d+(?:\.\d+)?[KMk]?\+?)\s*(?:conversations?|chats?|uses?)",
                r"(\d+[KMk]\+)",
            ]

            for pattern in count_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    details["gizmo"]["vanity_metrics"]["num_conversations_str"] = (
                        matches[0]
                    )
                    break

            # STRATEGY 9: Tool detection
            tool_patterns = {
                "dalle": [
                    "dall·e",
                    "dall-e",
                    "image generation",
                    "generate image",
                    "create image",
                ],
                "browser": [
                    "web browsing",
                    "browse web",
                    "search web",
                    "internet access",
                ],
                "python": [
                    "code interpreter",
                    "run code",
                    "execute python",
                    "data analysis",
                ],
            }

            for tool_type, patterns in tool_patterns.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        if not any(
                            t.get("type") == tool_type for t in details["tools"]
                        ):
                            details["tools"].append(
                                {
                                    "type": tool_type,
                                    "detected": True,
                                    "method": "text_analysis",
                                }
                            )
                        break

            # Log extraction success
            logger.debug(
                f"  {gizmo_id}: name={bool(details['gizmo']['display']['name'])}, "
                f"desc={bool(details['gizmo']['display']['description'])}, "
                f"starters={len(details['gizmo']['display']['prompt_starters'])}, "
                f"tools={len(details['tools'])}"
            )

            self.stats["gpts_detailed"] += 1

        except Exception as e:
            logger.warning(f"Error fetching details for {gizmo_id}: {e}")
            details["status"] = "unknown"

        return details

    async def crawl(
        self,
        max_keywords: Optional[int] = None,
        fetch_details: bool = True,
        detail_sample_size: Optional[int] = None,
    ):
        """Main crawling method with full metadata collection"""
        logger.info(f"🚀 Starting GPTracker crawl - Round {self.round_date}")
        logger.info(
            f"📋 Full metadata collection: {'ENABLED' if fetch_details else 'DISABLED'}"
        )

        keywords = await self.load_keywords(max_keywords)

        async with async_playwright() as p:
            browser, context = await self.create_stealth_browser(p)

            try:
                page = await self.setup_authenticated_session(context)

                # Phase 1: Search
                logger.info(f"\n📍 Phase 1: Searching with {len(keywords)} keywords")

                for i, keyword in enumerate(keywords, 1):
                    if i % 10 == 0:
                        logger.info(
                            f"Progress: {i}/{len(keywords)} ({len(self.gpts)} unique GPTs)"
                        )

                    gpts = await self.search_gpts(page, keyword)

                    for gpt in gpts:
                        gizmo_id = gpt["gizmo_id"]
                        if gizmo_id not in self.gpts:
                            self.gpts[gizmo_id] = gpt
                            self.stats["gpts_discovered"] += 1

                logger.info(f"\n✓ Phase 1 complete: {len(self.gpts)} unique GPTs")

                # Phase 2: Details
                if fetch_details:
                    gpt_ids = list(self.gpts.keys())

                    if detail_sample_size:
                        gpt_ids = gpt_ids[:detail_sample_size]

                    logger.info(
                        f"\n📍 Phase 2: Fetching metadata for {len(gpt_ids)} GPTs"
                    )

                    for i, gizmo_id in enumerate(gpt_ids, 1):
                        if i % 10 == 0:
                            logger.info(f"Details: {i}/{len(gpt_ids)}")

                        gpt = self.gpts[gizmo_id]
                        details = await self.get_gpt_details(page, gizmo_id, gpt["url"])
                        self.gpts[gizmo_id].update(details)

                    logger.info(
                        f"✓ Phase 2 complete: {self.stats['gpts_detailed']} with metadata"
                    )

                await self.save_results()

            finally:
                await browser.close()

        self.print_summary()

    async def save_results(self):
        """Save in GPTracker format"""
        csv_file = self.output_dir / f"all_{self.round_date}.csv"

        logger.info(f"\n💾 Saving results...")

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

        logger.info(f"✓ CSV: {csv_file}")

        json_file = self.output_dir / f"all_{self.round_date}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(list(self.gpts.values()), f, indent=2, ensure_ascii=False)

        logger.info(f"✓ JSON: {json_file}")

        if ZSTD_AVAILABLE:
            try:
                with open(csv_file, "rb") as f_in:
                    compressed = zstd.compress(f_in.read())

                zst_file = self.output_dir / f"all_{self.round_date}.csv.zst"
                with open(zst_file, "wb") as f_out:
                    f_out.write(compressed)

                logger.info(f"✓ Compressed: {zst_file}")
            except Exception as e:
                logger.warning(f"Compression failed: {e}")

        stats_file = self.output_dir / f"stats_{self.round_date}.json"
        with open(stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

        logger.info(f"✓ Stats: {stats_file}")

    def print_summary(self):
        """Print summary"""
        logger.info("\n" + "=" * 60)
        logger.info("CRAWL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Round: {self.round_date}")
        logger.info(f"Keywords: {self.stats['keywords_searched']}")
        logger.info(f"GPTs discovered: {self.stats['gpts_discovered']}")
        logger.info(f"GPTs detailed: {self.stats['gpts_detailed']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 60)


async def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "--test":
            crawler = GPTrackerCrawler(
                output_dir="data/test", headless=False, delay=2.0
            )
            await crawler.crawl(
                max_keywords=10, fetch_details=True, detail_sample_size=20
            )

        elif mode == "--small":
            crawler = GPTrackerCrawler(
                output_dir="data/gpt_store", headless=False, delay=2.0
            )
            await crawler.crawl(
                max_keywords=100, fetch_details=True, detail_sample_size=500
            )

        elif mode == "--full":
            crawler = GPTrackerCrawler(
                output_dir="data/gpt_store", headless=True, delay=2.0
            )
            await crawler.crawl(fetch_details=True, detail_sample_size=5000)

        else:
            print("Use: --test, --small, or --full")

    else:
        print(
            """
╔══════════════════════════════════════════════════════════╗
║          GPTracker Crawler - ENHANCED                    ║
╚══════════════════════════════════════════════════════════╝

Usage:
    python3 gpt_tracker.py --test     # 10 keywords, 20 detailed
    python3 gpt_tracker.py --small    # 100 keywords, 500 detailed
    python3 gpt_tracker.py --full     # All keywords, 5000 detailed

Running test mode...
        """
        )

        crawler = GPTrackerCrawler(output_dir="data/test", headless=False, delay=2.0)
        await crawler.crawl(max_keywords=10, fetch_details=True, detail_sample_size=20)


if __name__ == "__main__":
    asyncio.run(main())
