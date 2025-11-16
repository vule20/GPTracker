"""
GPTracker: Complete Implementation - PRODUCTION READY
Optimized for actual GPT Store HTML structure

Based on real interface analysis and paper requirements
Author: Updated for class project reproduction
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
    """
    Enhanced crawler matching actual GPT Store structure
    Extracts all available metadata for paper reproduction
    """

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
            "extraction_quality": {
                "name": 0,
                "description": 0,
                "starters": 0,
                "author": 0,
                "rating": 0,
                "conversations": 0,
                "tools": 0,
            },
        }

    async def load_keywords(self, max_keywords: Optional[int] = None) -> List[str]:
        """Load search keywords from file"""
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
        """Default keywords for testing"""
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
            "image",
            "video",
            "design",
            "research",
            "analysis",
            "marketing",
        ]

    async def create_stealth_browser(
        self, playwright
    ) -> Tuple[Browser, BrowserContext]:
        """Create browser with anti-detection measures"""
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
        """Handle authentication and session management"""
        page = await context.new_page()
        cookies_file = self.output_dir / "session_cookies.json"

        # Try to load existing session
        if cookies_file.exists():
            try:
                with open(cookies_file, "r") as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                logger.info("Loaded existing session")

                # Verify session is valid
                await page.goto("https://chatgpt.com/gpts", timeout=30000)
                await asyncio.sleep(3)

                content = await page.content()
                if "Error loading" not in content and "Sign up" not in content:
                    logger.info("✓ Session valid")
                    return page
                else:
                    logger.warning("Session expired, need to re-authenticate")
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

        # Need authentication
        logger.info("🔐 Authentication required")
        logger.info("Please complete login in the browser window...")

        await page.goto("https://chatgpt.com/", timeout=30000)
        await asyncio.sleep(3)

        content = await page.content()
        if "Sign up" in content or "Log in" in content:
            logger.warning("⚠️  Please log in and complete any verification")
            input("\n✋ Press Enter after you've logged in and see the GPT Store...")

        # Navigate to GPT Store to confirm access
        await page.goto("https://chatgpt.com/gpts", timeout=30000)
        await asyncio.sleep(2)

        # Save session
        cookies = await context.cookies()
        with open(cookies_file, "w") as f:
            json.dump(cookies, f)
        logger.info(f"✓ Session saved to {cookies_file}")

        return page

    async def search_gpts(self, page: Page, keyword: str) -> List[Dict]:
        """Search GPT Store for a keyword"""
        gpts = []
        search_url = f"https://chatgpt.com/gpts?q={keyword}"

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(self.delay)

            # Scroll to load more results
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

            # Extract GPT links
            links = await page.query_selector_all('a[href*="/g/"]')

            seen_ids = set()
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href or "/g/" not in href:
                        continue

                    # Extract gizmo_id from URL
                    match = re.search(r"/g/(g-[a-zA-Z0-9]+)", href)
                    if not match:
                        continue

                    gizmo_id = match.group(1)

                    # Avoid duplicates
                    if gizmo_id in seen_ids:
                        continue
                    seen_ids.add(gizmo_id)

                    gpt_data = {
                        "gizmo_id": gizmo_id,
                        "from": "search",
                        "url": (
                            f"https://chatgpt.com{href}"
                            if href.startswith("/")
                            else href
                        ),
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
        Extract complete metadata from GPT page
        Optimized for actual HTML structure
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
                "created_at": None,  # Not available on public page
                "updated_at": None,  # Not available on public page
                "tags": [],
                "vanity_metrics": {
                    "num_conversations": None,
                    "num_conversations_str": None,
                    "rating": None,
                    "rating_count": None,
                    "rank": None,
                    "rank_category": None,
                },
            },
            "tools": [],
            "files": [],  # Not available on public page
            "status": "unknown",
            "checked_at": datetime.now().isoformat(),
        }

        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)

            if response and response.status == 404:
                details["status"] = "unavailable"
                return details

            # Wait for dynamic content to load
            await asyncio.sleep(4)

            # Get full page content
            content = await page.content()
            full_text = await page.evaluate("() => document.body.innerText")

            if "not found" in content.lower() or "doesn't exist" in content.lower():
                details["status"] = "unavailable"
                return details

            details["status"] = "available"

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 1: GPT Name
            # ═══════════════════════════════════════════════════════════
            # Look for main heading
            name_selectors = [
                "div.text-2xl.font-semibold",
                "h1",
                "h2",
                '[class*="font-semibold"][class*="text-2xl"]',
            ]

            for selector in name_selectors:
                try:
                    name_elem = await page.query_selector(selector)
                    if name_elem:
                        name_text = await name_elem.text_content()
                        if name_text and len(name_text.strip()) > 2:
                            details["gizmo"]["display"]["name"] = name_text.strip()
                            self.stats["extraction_quality"]["name"] += 1
                            break
                except:
                    continue

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 2: Description
            # ═══════════════════════════════════════════════════════════
            # Pattern: "4.0 ★ - [description text]"
            desc_pattern = r"[\d\.]+\s*[★⭐]\s*-\s*(.+?)(?:\n|$)"
            desc_match = re.search(desc_pattern, full_text)
            if desc_match:
                description = desc_match.group(1).strip()
                if len(description) > 20:
                    details["gizmo"]["display"]["description"] = description
                    self.stats["extraction_quality"]["description"] += 1

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 3: Conversation Starters (FROM HTML!)
            # ═══════════════════════════════════════════════════════════
            starter_links = await page.query_selector_all('a[href*="?q="]')
            starters = []

            for link in starter_links:
                try:
                    # Get the text inside the link
                    text_elem = await link.query_selector("div.line-clamp-2")
                    if text_elem:
                        text = await text_elem.text_content()
                        if text and 10 < len(text.strip()) < 300:
                            clean_text = text.strip()
                            if clean_text not in starters:
                                starters.append(clean_text)
                except:
                    continue

            if starters:
                details["gizmo"]["display"]["prompt_starters"] = starters
                self.stats["extraction_quality"]["starters"] += 1

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 4: Author
            # ═══════════════════════════════════════════════════════════
            # Pattern: "By [author name]"
            author_patterns = [
                r"By\s+([^\n•]+?)(?:\n|•|$)",
                r"By\s+([\w\s\.]+)",
            ]

            for pattern in author_patterns:
                author_match = re.search(pattern, full_text)
                if author_match:
                    author_name = author_match.group(1).strip()
                    # Clean up verification badges
                    author_name = re.sub(r"\s*[✓✔👤]\s*", "", author_name)
                    if 2 < len(author_name) < 100:
                        details["gizmo"]["author"]["display_name"] = author_name
                        self.stats["extraction_quality"]["author"] += 1
                        break

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 5: Metrics (Rating, Conversations, Rank)
            # ═══════════════════════════════════════════════════════════

            # Rating (e.g., "4.0 ★")
            rating_match = re.search(r"(\d+\.\d+)\s*[★⭐]", full_text)
            if rating_match:
                details["gizmo"]["vanity_metrics"]["rating"] = float(
                    rating_match.group(1)
                )
                self.stats["extraction_quality"]["rating"] += 1

            # Rating count (e.g., "Ratings (100K+)")
            rating_count_match = re.search(r"Ratings?\s*\(([^)]+)\)", full_text)
            if rating_count_match:
                details["gizmo"]["vanity_metrics"]["rating_count"] = (
                    rating_count_match.group(1)
                )

            # Rank (e.g., "#4 in Productivity (EN)")
            rank_match = re.search(r"#(\d+)\s+in\s+([^\n]+?)(?:\n|$)", full_text)
            if rank_match:
                details["gizmo"]["vanity_metrics"]["rank"] = int(rank_match.group(1))
                category = rank_match.group(2).strip()
                # Remove language code if present
                category = re.sub(r"\s*\([A-Z]{2}\)\s*$", "", category)
                details["gizmo"]["vanity_metrics"]["rank_category"] = category

                # Add to categories
                if category.lower() not in [
                    c.lower() for c in details["gizmo"]["display"]["categories"]
                ]:
                    details["gizmo"]["display"]["categories"].append(category)

            # Conversation count (e.g., "12M+ Conversations")
            conv_patterns = [
                r"([\d\.]+[KMBkmb]?\+?)\s+Conversations?",
                r"Conversations?\s*\n\s*([\d\.]+[KMBkmb]?\+?)",
            ]

            for pattern in conv_patterns:
                conv_match = re.search(pattern, full_text, re.IGNORECASE)
                if conv_match:
                    details["gizmo"]["vanity_metrics"]["num_conversations_str"] = (
                        conv_match.group(1)
                    )
                    self.stats["extraction_quality"]["conversations"] += 1
                    break

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 6: Tools/Capabilities (FROM CAPABILITIES SECTION!)
            # ═══════════════════════════════════════════════════════════

            # Look for the Capabilities section
            capabilities_text = ""

            # Try to find "Capabilities" heading and get text after it
            if "Capabilities" in full_text:
                cap_index = full_text.find("Capabilities")
                # Get next 500 characters after "Capabilities"
                capabilities_text = full_text[cap_index : cap_index + 500]

            tools_found = []

            # Check for each tool type
            if "DALL" in capabilities_text or "Image Generation" in capabilities_text:
                tools_found.append(
                    {
                        "id": "dalle-tool",
                        "type": "dalle",
                        "settings": None,
                        "metadata": None,
                    }
                )

            if (
                "Code Interpreter" in capabilities_text
                or "Data Analysis" in capabilities_text
            ):
                tools_found.append(
                    {
                        "id": "python-tool",
                        "type": "python",
                        "settings": None,
                        "metadata": None,
                    }
                )

            if "Web Search" in capabilities_text or "Web Browsing" in capabilities_text:
                tools_found.append(
                    {
                        "id": "browser-tool",
                        "type": "browser",
                        "settings": None,
                        "metadata": None,
                    }
                )

            # CRITICAL: Check for External APIs (Actions)
            if "Actions" in capabilities_text:
                tools_found.append(
                    {
                        "id": "external-api",
                        "type": "external_api",
                        "settings": None,
                        "metadata": {"note": "Has external API integration"},
                    }
                )

            if tools_found:
                details["tools"] = tools_found
                self.stats["extraction_quality"]["tools"] += 1

            # ═══════════════════════════════════════════════════════════
            # EXTRACTION STRATEGY 7: Categories (from keywords)
            # ═══════════════════════════════════════════════════════════
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
            for keyword in category_keywords:
                if (
                    keyword in text_lower
                    and keyword not in details["gizmo"]["display"]["categories"]
                ):
                    details["gizmo"]["display"]["categories"].append(keyword)
                    if len(details["gizmo"]["display"]["categories"]) >= 5:
                        break

            # ═══════════════════════════════════════════════════════════
            # Log extraction success
            # ═══════════════════════════════════════════════════════════
            logger.debug(
                f"  {gizmo_id}: "
                f"name={bool(details['gizmo']['display']['name'])}, "
                f"desc={bool(details['gizmo']['display']['description'])}, "
                f"starters={len(details['gizmo']['display']['prompt_starters'])}, "
                f"author={bool(details['gizmo']['author']['display_name'])}, "
                f"rating={bool(details['gizmo']['vanity_metrics']['rating'])}, "
                f"conv={bool(details['gizmo']['vanity_metrics']['num_conversations_str'])}, "
                f"tools={len(details['tools'])}"
            )

            self.stats["gpts_detailed"] += 1

        except Exception as e:
            logger.warning(f"Error fetching details for {gizmo_id}: {e}")
            details["status"] = "error"
            self.stats["errors"] += 1

        return details

    async def crawl(
        self,
        max_keywords: Optional[int] = None,
        fetch_details: bool = True,
        detail_sample_size: Optional[int] = None,
    ):
        """Main crawling orchestrator"""
        logger.info(f"🚀 Starting GPTracker crawl - Round {self.round_date}")
        logger.info(
            f"📋 Metadata extraction: {'ENABLED' if fetch_details else 'DISABLED'}"
        )

        keywords = await self.load_keywords(max_keywords)

        async with async_playwright() as p:
            browser, context = await self.create_stealth_browser(p)

            try:
                page = await self.setup_authenticated_session(context)

                # ═══════════════════════════════════════════════════════════
                # PHASE 1: Search and Discovery
                # ═══════════════════════════════════════════════════════════
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

                logger.info(
                    f"\n✓ Phase 1 complete: {len(self.gpts)} unique GPTs discovered"
                )

                # ═══════════════════════════════════════════════════════════
                # PHASE 2: Detailed Metadata Collection
                # ═══════════════════════════════════════════════════════════
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

                        # Merge details into existing GPT data
                        self.gpts[gizmo_id].update(details)

                    logger.info(
                        f"✓ Phase 2 complete: {self.stats['gpts_detailed']} GPTs with metadata"
                    )

                await self.save_results()

            finally:
                await browser.close()

        self.print_summary()

    async def save_results(self):
        """Save results in GPTracker paper format"""
        csv_file = self.output_dir / f"all_{self.round_date}.csv"

        logger.info(f"\n💾 Saving results...")

        # Save in paper format: gizmo_id, from, json, status, round
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

        logger.info(f"✓ CSV saved: {csv_file}")

        # Also save as readable JSON
        json_file = self.output_dir / f"all_{self.round_date}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(list(self.gpts.values()), f, indent=2, ensure_ascii=False)

        logger.info(f"✓ JSON saved: {json_file}")

        # Compress if available
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

        # Save statistics
        stats_file = self.output_dir / f"stats_{self.round_date}.json"
        with open(stats_file, "w") as f:
            json.dump(self.stats, f, indent=2)

        logger.info(f"✓ Stats saved: {stats_file}")

    def print_summary(self):
        """Print collection summary with quality metrics"""
        logger.info("\n" + "=" * 70)
        logger.info("CRAWL SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Round Date:        {self.round_date}")
        logger.info(f"Keywords Searched: {self.stats['keywords_searched']}")
        logger.info(f"GPTs Discovered:   {self.stats['gpts_discovered']}")
        logger.info(f"GPTs Detailed:     {self.stats['gpts_detailed']}")
        logger.info(f"Errors:            {self.stats['errors']}")
        logger.info("")
        logger.info("EXTRACTION QUALITY:")
        logger.info(
            f"  Names:        {self.stats['extraction_quality']['name']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Descriptions: {self.stats['extraction_quality']['description']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Starters:     {self.stats['extraction_quality']['starters']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Authors:      {self.stats['extraction_quality']['author']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Ratings:      {self.stats['extraction_quality']['rating']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Conversations:{self.stats['extraction_quality']['conversations']}/{self.stats['gpts_detailed']}"
        )
        logger.info(
            f"  Tools:        {self.stats['extraction_quality']['tools']}/{self.stats['gpts_detailed']}"
        )
        logger.info("=" * 70)


async def main():
    """Main entry point with different modes"""
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "--test":
            # Quick test: 10 keywords, 20 detailed GPTs
            logger.info("🧪 TEST MODE: Small sample for testing")
            crawler = GPTrackerCrawler(
                output_dir="data/test", headless=False, delay=2.0
            )
            await crawler.crawl(
                max_keywords=10, fetch_details=True, detail_sample_size=20
            )

        elif mode == "--small":
            # Small scale: Good for class project
            logger.info("📚 SMALL MODE: Class project scale")
            crawler = GPTrackerCrawler(
                output_dir="data/gpt_store", headless=False, delay=2.0
            )
            await crawler.crawl(
                max_keywords=500, fetch_details=True, detail_sample_size=2000
            )

        elif mode == "--medium":
            # Medium scale: Better coverage
            logger.info("📊 MEDIUM MODE: Good coverage")
            crawler = GPTrackerCrawler(
                output_dir="data/gpt_store", headless=True, delay=2.0
            )
            await crawler.crawl(
                max_keywords=1500, fetch_details=True, detail_sample_size=5000
            )

        elif mode == "--full":
            # Full replication attempt
            logger.info("🔬 FULL MODE: Paper replication scale")
            crawler = GPTrackerCrawler(
                output_dir="data/gpt_store", headless=True, delay=1.5
            )
            await crawler.crawl(
                max_keywords=10000, fetch_details=True, detail_sample_size=10000
            )

        else:
            print("Unknown mode. Use: --test, --small, --medium, or --full")

    else:
        # Default: show help
        print(
            """
╔══════════════════════════════════════════════════════════════════╗
║              GPTracker Crawler - Production Ready                ║
║                    Updated for Paper Reproduction                ║
╚══════════════════════════════════════════════════════════════════╝

USAGE:
    python3 gpt_tracker_fixed.py [MODE]

MODES:
    --test      Quick test (10 keywords, 20 detailed GPTs)
                ~5 minutes, good for testing setup
    
    --small     Class project scale (500 keywords, 2K GPTs)
                ~2-4 hours, recommended for class projects
    
    --medium    Good coverage (1500 keywords, 5K GPTs)
                ~6-8 hours, better for analysis
    
    --full      Paper replication (10K keywords, 10K GPTs)
                ~24+ hours, full replication attempt

FEATURES:
    ✓ Extracts all available metadata from GPT pages
    ✓ Matches actual HTML structure
    ✓ Handles authentication
    ✓ Quality tracking
    ✓ Paper-compatible output format

DATA EXTRACTED:
    ✓ Name, description, conversation starters
    ✓ Author information
    ✓ Ratings and review counts
    ✓ Conversation counts
    ✓ Rankings and categories
    ✓ Tools (DALL-E, Code, Browser, External APIs)

LIMITATIONS:
    ✗ Creation/update dates (not shown on public pages)
    ✗ Knowledge files (not shown on public pages)

OUTPUT:
    - data/all_YYYY-MM-DD.csv  (Paper format)
    - data/all_YYYY-MM-DD.json (Readable format)
    - data/stats_YYYY-MM-DD.json (Quality metrics)

Running test mode by default...
        """
        )

        # Run test mode
        crawler = GPTrackerCrawler(output_dir="data/test", headless=False, delay=2.0)
        await crawler.crawl(max_keywords=10, fetch_details=True, detail_sample_size=20)


if __name__ == "__main__":
    asyncio.run(main())
