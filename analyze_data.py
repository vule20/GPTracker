# analyze_data.py
# Created on: 2025-11-16 10:59:42
# Author: VuLe@macbook
# Last updated: 2025-11-16 10:59:42
# Last modified by: VuLe@macbook


"""
GPTracker Data Analyzer
Analyzes collected GPT data and shows quality metrics
"""

import json
import csv
from pathlib import Path
from collections import Counter
import sys


def analyze_gpt_data(data_file: str):
    """Analyze the collected GPT data"""

    print(f"\n{'='*70}")
    print(f"ANALYZING: {data_file}")
    print(f"{'='*70}\n")

    # Load data
    if data_file.endswith(".csv"):
        data = load_from_csv(data_file)
    elif data_file.endswith(".json"):
        data = load_from_json(data_file)
    else:
        print("❌ File must be .csv or .json")
        return

    if not data:
        print("❌ No data found")
        return

    print(f"📊 Total GPTs: {len(data)}\n")

    # Analyze fields
    analyze_fields(data)

    # Analyze tools
    analyze_tools(data)

    # Analyze categories
    analyze_categories(data)

    # Analyze ratings
    analyze_ratings(data)

    # Show sample
    show_sample(data)


def load_from_csv(filepath: str):
    """Load data from CSV file"""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                gpt_data = json.loads(row["json"])
                data.append(gpt_data)
            except:
                continue
    return data


def load_from_json(filepath: str):
    """Load data from JSON file"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_fields(data):
    """Analyze field extraction quality"""
    print("🔍 FIELD EXTRACTION QUALITY:")
    print("-" * 70)

    counts = {
        "name": 0,
        "description": 0,
        "author": 0,
        "starters": 0,
        "rating": 0,
        "conversations": 0,
        "tools": 0,
        "categories": 0,
    }

    for gpt in data:
        gizmo = gpt.get("gizmo", {})
        display = gizmo.get("display", {})
        author = gizmo.get("author", {})
        metrics = gizmo.get("vanity_metrics", {})

        if display.get("name"):
            counts["name"] += 1
        if display.get("description"):
            counts["description"] += 1
        if author.get("display_name"):
            counts["author"] += 1
        if display.get("prompt_starters"):
            counts["starters"] += 1
        if metrics.get("rating"):
            counts["rating"] += 1
        if metrics.get("num_conversations_str"):
            counts["conversations"] += 1
        if gpt.get("tools"):
            counts["tools"] += 1
        if display.get("categories"):
            counts["categories"] += 1

    total = len(data)
    for field, count in counts.items():
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"{field:15} {count:5}/{total:5} ({pct:5.1f}%) {bar}")

    print()


def analyze_tools(data):
    """Analyze tool usage"""
    print("🛠️  TOOL USAGE:")
    print("-" * 70)

    tool_counts = Counter()
    gpts_with_tools = 0

    for gpt in data:
        tools = gpt.get("tools", [])
        if tools:
            gpts_with_tools += 1
            for tool in tools:
                tool_type = tool.get("type", "unknown")
                tool_counts[tool_type] += 1

    print(
        f"GPTs with tools: {gpts_with_tools}/{len(data)} ({gpts_with_tools/len(data)*100:.1f}%)\n"
    )

    for tool, count in tool_counts.most_common():
        pct = (count / len(data) * 100) if len(data) > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"{tool:15} {count:5} ({pct:5.1f}%) {bar}")

    print()


def analyze_categories(data):
    """Analyze categories"""
    print("📁 TOP CATEGORIES:")
    print("-" * 70)

    category_counts = Counter()

    for gpt in data:
        gizmo = gpt.get("gizmo", {})
        display = gizmo.get("display", {})
        categories = display.get("categories", [])

        for cat in categories:
            category_counts[cat.lower()] += 1

    for cat, count in category_counts.most_common(15):
        pct = (count / len(data) * 100) if len(data) > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"{cat:20} {count:5} ({pct:5.1f}%) {bar}")

    print()


def analyze_ratings(data):
    """Analyze ratings"""
    print("⭐ RATING DISTRIBUTION:")
    print("-" * 70)

    ratings = []
    for gpt in data:
        gizmo = gpt.get("gizmo", {})
        metrics = gizmo.get("vanity_metrics", {})
        rating = metrics.get("rating")
        if rating:
            ratings.append(rating)

    if not ratings:
        print("No rating data found\n")
        return

    avg_rating = sum(ratings) / len(ratings)
    print(f"GPTs with ratings: {len(ratings)}/{len(data)}")
    print(f"Average rating: {avg_rating:.2f}\n")

    # Distribution
    rating_counts = Counter([int(r) for r in ratings])
    for i in range(5, 0, -1):
        count = rating_counts.get(i, 0)
        pct = (count / len(ratings) * 100) if len(ratings) > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"{i} stars: {count:5} ({pct:5.1f}%) {bar}")

    print()


def show_sample(data):
    """Show a sample GPT"""
    print("📝 SAMPLE GPT (First detailed one):")
    print("-" * 70)

    # Find a GPT with good data
    sample = None
    for gpt in data:
        gizmo = gpt.get("gizmo", {})
        display = gizmo.get("display", {})
        if display.get("name") and display.get("description"):
            sample = gpt
            break

    if not sample:
        print("No detailed GPT found\n")
        return

    gizmo = sample.get("gizmo", {})
    display = gizmo.get("display", {})
    author = gizmo.get("author", {})
    metrics = gizmo.get("vanity_metrics", {})

    print(f"ID:          {gizmo.get('id', 'N/A')}")
    print(f"Name:        {display.get('name', 'N/A')}")
    print(f"Description: {display.get('description', 'N/A')[:100]}...")
    print(f"Author:      {author.get('display_name', 'N/A')}")
    print(f"Rating:      {metrics.get('rating', 'N/A')}")
    print(f"Convs:       {metrics.get('num_conversations_str', 'N/A')}")
    print(
        f"Rank:        #{metrics.get('rank', 'N/A')} in {metrics.get('rank_category', 'N/A')}"
    )

    starters = display.get("prompt_starters", [])
    if starters:
        print(f"Starters:    {len(starters)} starters")
        for i, starter in enumerate(starters[:3], 1):
            print(f"  {i}. {starter[:60]}...")

    tools = sample.get("tools", [])
    if tools:
        print(f"Tools:       {', '.join([t.get('type', '?') for t in tools])}")

    categories = display.get("categories", [])
    if categories:
        print(f"Categories:  {', '.join(categories[:5])}")

    print()


def main():
    if len(sys.argv) < 2:
        print(
            """
Usage: python3 analyze_data.py <data_file>

Example:
    python3 analyze_data.py data/test/all_2024-11-17.json
    python3 analyze_data.py data/gpt_store/all_2024-11-17.csv
        """
        )

        # Try to find latest file
        data_dirs = [Path("data/test"), Path("data/gpt_store"), Path("data")]
        for data_dir in data_dirs:
            if data_dir.exists():
                json_files = list(data_dir.glob("all_*.json"))
                if json_files:
                    latest = max(json_files, key=lambda p: p.stat().st_mtime)
                    print(f"\n📁 Found: {latest}")
                    print("Analyzing...\n")
                    analyze_gpt_data(str(latest))
                    return

        print("❌ No data files found")
        return

    analyze_gpt_data(sys.argv[1])


if __name__ == "__main__":
    main()
