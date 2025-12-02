#!/usr/bin/env python3
"""
Enhanced Figure 6 - detects ALL languages in the data
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

try:
    from langdetect import detect, detect_langs
    from langdetect.lang_detect_exception import LangDetectException
except:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "langdetect", "--user", "-q"])
    from langdetect import detect, detect_langs
    from langdetect.lang_detect_exception import LangDetectException

# Comprehensive language mapping
LANG_MAP = {
    'en': 'English',
    'ko': 'Korean', 
    'es': 'Spanish',
    'zh-cn': 'Chinese',
    'zh-tw': 'Chinese',
    'pt': 'Portuguese',
    'de': 'German',
    'fr': 'French',
    'ru': 'Russian',
    'it': 'Italian',
    'ja': 'Japanese',
    'vi': 'Vietnamese',
    'el': 'Greek',
    'tr': 'Turkish',
    'pl': 'Polish',
    'nl': 'Dutch',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'th': 'Thai',
    'id': 'Indonesian',
    'ro': 'Romanian',
    'cs': 'Czech',
    'sv': 'Swedish',
    'da': 'Danish',
    'no': 'Norwegian',
    'fi': 'Finnish',
    'hu': 'Hungarian',
    'uk': 'Ukrainian',
    'bg': 'Bulgarian',
    'hr': 'Croatian',
    'sk': 'Slovak',
    'sl': 'Slovenian',
    'lt': 'Lithuanian',
    'lv': 'Latvian',
    'et': 'Estonian',
    'fa': 'Persian',
    'he': 'Hebrew',
    'ur': 'Urdu',
    'bn': 'Bengali',
    'ta': 'Tamil',
    'te': 'Telugu',
    'mr': 'Marathi',
    'ml': 'Malayalam',
    'kn': 'Kannada',
    'pa': 'Punjabi',
    'gu': 'Gujarati',
    'sw': 'Swahili',
    'af': 'Afrikaans',
    'ca': 'Catalan',
    'eu': 'Basque',
    'gl': 'Galician',
    'cy': 'Welsh',
    'is': 'Icelandic',
    'mk': 'Macedonian',
    'sq': 'Albanian',
    'sr': 'Serbian',
    'bs': 'Bosnian',
    'ms': 'Malay',
    'tl': 'Tagalog',
    'ne': 'Nepali',
    'si': 'Sinhala',
    'km': 'Khmer',
    'lo': 'Lao',
    'my': 'Burmese',
    'ka': 'Georgian',
    'hy': 'Armenian',
    'az': 'Azerbaijani',
    'kk': 'Kazakh',
    'uz': 'Uzbek',
    'mn': 'Mongolian'
}

def detect_language(text):
    """Detect language from text with fallback"""
    if pd.isna(text) or str(text).strip() == '':
        return 'English'
    
    try:
        # Use langdetect
        text_clean = str(text)[:1000]  # Use first 1000 chars for speed
        lang_code = detect(text_clean)
        
        # Map to full language name
        return LANG_MAP.get(lang_code, lang_code.upper())
    
    except LangDetectException:
        # Fallback: check for obvious indicators
        text_lower = str(text).lower()
        
        # Korean
        if any('\u3131' <= c <= '\u318e' or '\uac00' <= c <= '\ud7a3' for c in text[:100]):
            return 'Korean'
        # Chinese
        if any('\u4e00' <= c <= '\u9fff' for c in text[:100]):
            return 'Chinese'
        # Japanese
        if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text[:100]):
            return 'Japanese'
        # Arabic
        if any('\u0600' <= c <= '\u06ff' for c in text[:100]):
            return 'Arabic'
        # Cyrillic (Russian, Ukrainian, etc.)
        if any('\u0400' <= c <= '\u04ff' for c in text[:100]):
            return 'Russian'
        
        return 'English'
    
    except Exception:
        return 'English'

def generate_figure6(scenario_dir, output_file, top_n=15):
    """Generate Figure 6 with all detected languages"""
    print("="*60)
    print("Figure 6: Language Statistics (Enhanced)")
    print("="*60)
    
    scenario_dir = Path(scenario_dir)
    scenario_files = list(scenario_dir.glob('scenario_*.csv'))
    
    if len(scenario_files) == 0:
        print("ERROR: No scenario files found!")
        return False
    
    print(f"\nDetecting languages in {len(scenario_files)} scenarios...\n")
    
    lang_data = {}
    all_languages_found = set()
    
    for file in scenario_files:
        scenario = file.stem.replace('scenario_', '').replace('_', ' ').title()
        df = pd.read_csv(file)
        
        # Detect languages
        print(f"Processing {scenario}...")
        df['language'] = df.apply(
            lambda r: detect_language(
                f"{r.get('name', '')} {r.get('desc', '')}"
            ), axis=1
        )
        
        lang_counts = df['language'].value_counts()
        lang_data[scenario] = lang_counts.to_dict()
        all_languages_found.update(lang_counts.index)
        
        print(f"  {scenario:22s}: {len(df):4d} GPTs, {len(lang_counts)} languages")
        print(f"    Top 3: {', '.join([f'{l}({c})' for l, c in lang_counts.head(3).items()])}")
    
    print(f"\n{'='*60}")
    print(f"Total unique languages detected: {len(all_languages_found)}")
    print(f"{'='*60}\n")
    
    # Calculate total count per language
    lang_totals = {}
    for lang in all_languages_found:
        lang_totals[lang] = sum(counts.get(lang, 0) for counts in lang_data.values())
    
    # Sort by total count
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    
    print("All languages found (sorted by count):")
    for i, (lang, count) in enumerate(sorted_langs, 1):
        print(f"  {i:2d}. {lang:20s}: {count:4d} GPTs")
    
    # Select top N languages for visualization
    selected_langs = [l for l, _ in sorted_langs[:top_n]]
    
    print(f"\nUsing top {top_n} languages for heatmap\n")
    
    # Create matrix for heatmap
    scenarios = sorted(lang_data.keys())
    matrix = np.zeros((len(scenarios), len(selected_langs)))
    
    for i, scenario in enumerate(scenarios):
        for j, lang in enumerate(selected_langs):
            matrix[i, j] = lang_data[scenario].get(lang, 0)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(16, 9))
    
    sns.heatmap(
        matrix,
        xticklabels=selected_langs,
        yticklabels=scenarios,
        annot=True,
        fmt='g',
        cmap='Blues',
        cbar_kws={'label': 'Number of GPTs'},
        linewidths=0.5,
        linecolor='white',
        ax=ax
    )
    
    ax.set_xlabel('Language', fontsize=12, fontweight='bold')
    ax.set_ylabel('Forbidden Scenario', fontsize=12, fontweight='bold')
    ax.set_title('Figure 6: Language statistics of misused GPTs.', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    
    # Also save detailed data
    matrix_df = pd.DataFrame(
        matrix,
        index=scenarios,
        columns=selected_langs
    )
    matrix_df.to_csv(output_file.replace('.png', '_data.csv'))
    print(f"✅ Saved: {output_file.replace('.png', '_data.csv')}")
    
    # Save full language statistics
    full_stats = pd.DataFrame(sorted_langs, columns=['Language', 'Total GPTs'])
    full_stats.to_csv(output_file.replace('.png', '_all_languages.csv'), index=False)
    print(f"✅ Saved: {output_file.replace('.png', '_all_languages.csv')}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python figure6_enhanced.py <scenario_dir> <output_file> [top_n_languages]")
        print("\nExample:")
        print("  python figure6_enhanced.py results/ results/figure6.png 20")
        sys.exit(1)
    
    scenario_dir = sys.argv[1]
    output_file = sys.argv[2]
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    
    success = generate_figure6(scenario_dir, output_file, top_n)
    
    sys.exit(0 if success else 1)