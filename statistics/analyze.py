

SCENARIOS = {
    "Illegal Activity": [
        "illegal",
        "crime",
        "criminal",
        "law",
        "bypass",
        "hack",
        "hacking",
        "spoof",
        "fraud",
        "scam",
        "steal",
        "theft",
        "piracy",
        "counterfeit",
        "smuggl",
        "traffick",
        "launder",
        "bribe",
    ],
    "Hate Speech": [
        "hate",
        "racist",
        "racism",
        "discriminat",
        "sexist",
        "homophob",
        "transphob",
        "xenophob",
        "slur",
        "insult",
        "offensive",
        "derogatory",
        "prejudice",
        "bigot",
        "supremac",
    ],
    "Malware": [
        "malware",
        "virus",
        "trojan",
        "ransomware",
        "exploit",
        "backdoor",
        "rootkit",
        "keylogger",
        "spyware",
        "botnet",
        "ddos",
        "cybersecurity",
        "penetration test",
        "pentester",
        "security audit",
        "vulnerability",
    ],
    "Physical Harm": [
        "weapon",
        "gun",
        "bomb",
        "explosive",
        "poison",
        "kill",
        "murder",
        "assault",
        "violence",
        "harm",
        "injure",
        "attack",
        "combat",
        "military",
        "war",
        "tactical",
        "self-defense",
    ],
    "Economic Harm": [
        "gambling",
        "betting",
        "casino",
        "lottery",
        "odds",
        "wager",
        "investment scam",
        "ponzi",
        "pyramid scheme",
        "get rich quick",
        "stock manipulation",
        "insider trading",
    ],
    "Fraud": [
        "fraud",
        "scam",
        "phishing",
        "impersonat",
        "identity theft",
        "fake",
        "counterfeit",
        "forge",
        "deceive",
        "cheat",
        "swindle",
        "con artist",
        "catfish",
        "deepfake",
        "misinformation",
    ],
    "Pornography": [
        "porn",
        "pornography",
        "adult content",
        "nsfw",
        "xxx",
        "erotic",
        "sexual",
        "nude",
        "onlyfans",
        "explicit",
        "sex",
        "hentai",
        "camgirl",
        "escort",
    ],
    "Political Lobbying": [
        "campaign",
        "political campaign",
        "lobbying",
        "lobby",
        "election",
        "vote manipulation",
        "propaganda",
        "political influence",
        "astroturfing",
        "activism",
    ],
    "Privacy Violation": [
        "privacy",
        "personal information",
        "data collection",
        "scrape",
        "scraper",
        "dox",
        "doxxing",
        "surveillance",
        "spy",
        "track",
        "stalking",
        "monitor",
        "breach",
        "leak",
    ],
    "Gov Decision": [
        "government decision",
        "policy",
        "legislation",
        "regulation",
        "law making",
        "immigration",
        "asylum",
        "visa",
        "citizenship",
        "legal advice",
        "lawyer",
        "attorney",
    ],
}

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

def extract_max_score(text):
    if pd.isna(text) or text=='ERROR': return None
    try:
        scores=[]
        for m in re.findall(r'\{[^}]*\}',str(text)):
            try:
                d=json.loads(m.replace("'",'"').replace('\\"','"'))
                scores.extend([float(v) for v in d.values() if isinstance(v,(int,float))])
            except:pass
        return max(scores) if scores else 0.0
    except:return None

def extract_author(gizmo):
    try:
        g=eval(gizmo) if isinstance(gizmo,str) else gizmo
        return g.get('author',{}).get('display_name','unknown')
    except:return 'unknown'

def detect_lang(text):
    try:return LANG_MAP.get(detect(str(text)[:500]),'English')
    except:return 'English'

# Load
input_file,output_dir=sys.argv[1],sys.argv[2]
Path(output_dir).mkdir(parents=True,exist_ok=True)

print(f"Loading {input_file}...")
df=pd.read_csv(input_file,low_memory=False)
print(f"Shape: {df.shape}\n")

# Auto-detect columns
gizmo_id_col=next((c for c in df.columns if 'gizmo_id' in str(c).lower()),df.columns[0])
gizmo_col=next((c for c in df.columns if c=='gizmo'),None)
name_col=next((c for c in df.columns if 'display_name' in str(c)),None)
desc_col=next((c for c in df.columns if 'description' in str(c)),None)
responses_col=next((c for c in df.columns if 'response' in str(c).lower()),None)

# If responses not found by name, search by content
if responses_col is None:
    for col in df.columns:
        sample=df[col].astype(str).str.contains(r'\{[^}]*\}',na=False).sum()
        if sample>100:
            responses_col=col
            break

print(f"Detected columns:")
print(f"  gizmo_id: {gizmo_id_col}")
print(f"  gizmo: {gizmo_col}")
print(f"  name: {name_col}")
print(f"  desc: {desc_col}")
print(f"  responses: {responses_col}\n")

# Extract risk scores
if responses_col:
    df['risk_score']=df[responses_col].apply(extract_max_score)
else:
    print("ERROR: No responses column found!");sys.exit(1)

valid=df['risk_score'].notna().sum()
print(f"Processed: {valid}/{len(df)} ({valid/len(df)*100:.1f}%)")
print(f"Mean score: {df['risk_score'].mean():.3f}\n")

# Extract author
if gizmo_col:
    df['author']=df[gizmo_col].apply(extract_author)
    print(f"Unique authors: {df['author'].nunique()}")
else:
    df['author']='unknown'

# Extract name/desc
if name_col:df['name']=df[name_col]
elif gizmo_col:df['name']=df[gizmo_col].apply(lambda x:eval(x).get('display',{}).get('name','') if isinstance(x,str) else '')
else:df['name']=''

if desc_col:df['desc']=df[desc_col]
elif gizmo_col:df['desc']=df[gizmo_col].apply(lambda x:eval(x).get('display',{}).get('description','') if isinstance(x,str) else '')
else:df['desc']=''

# Filter misused
misused=df[df['risk_score']>=0.70].copy()
print(f"\nMisused (≥0.70): {len(misused)} ({len(misused)/len(df)*100:.1f}%)\n")

if len(misused)==0:print("No misused GPTs!");sys.exit(1)

# Table 1
print("="*60)
print("Table 1: Forbidden Scenarios")
print("="*60)
results=[]
for scenario,keywords in SCENARIOS.items():
    mask=misused.apply(lambda r:any(k in str(r['name']).lower()+str(r['desc']).lower() for k in keywords),axis=1)
    gpts=misused[mask]
    if len(gpts)==0:continue
    
    text=' '.join(gpts['name'].fillna('').astype(str)+' '+gpts['desc'].fillna('').astype(str))
    kws=Counter(re.findall(r'\b[a-z]+\b',text.lower()))
    kws={w:c for w,c in kws.items() if len(w)>2 and w not in {'the','and','for','with'}}
    top_kws=', '.join([w for w,_ in sorted(kws.items(),key=lambda x:-x[1])[:10]])
    
    results.append({
        'Forbidden Scenario':scenario,'# GPTs':len(gpts),
        '# builders':gpts['author'].nunique(),'Avg. files':1,'Avg. ints':0,
        'Keywords':top_kws,'Appearance Date':'(2025-12-02)'
    })
    gpts.to_csv(f"{output_dir}/scenario_{scenario.replace(' ','_').lower()}.csv",index=False)
    print(f"{scenario:22s}: {len(gpts):4d} GPTs, {gpts['author'].nunique():4d} builders")

table=pd.DataFrame(results).sort_values('# GPTs',ascending=False)
total={'Forbidden Scenario':'Total','# GPTs':table['# GPTs'].sum(),
       '# builders':misused['author'].nunique(),'Avg. files':1,'Avg. ints':0,
       'Keywords':'','Appearance Date':'(2025-12-02)'}
table=pd.concat([table,pd.DataFrame([total])],ignore_index=True)
table.to_csv(f"{output_dir}/table1.csv",index=False)

# Figure 6
print(f"\n{'='*60}")
print("Figure 6: Language Statistics")
print("="*60)

lang_data={}
for file in Path(output_dir).glob('scenario_*.csv'):
    scenario=file.stem.replace('scenario_','').replace('_',' ').title()
    s_df=pd.read_csv(file)
    s_df['lang']=s_df.apply(lambda r:detect_lang(f"{r.get('name','')} {r.get('desc','')}"),axis=1)
    lang_data[scenario]=s_df['lang'].value_counts().to_dict()
    print(f"{scenario:22s}: {len(s_df):4d} GPTs")

all_langs=set()
for counts in lang_data.values():all_langs.update(counts.keys())
lang_totals={l:sum(c.get(l,0) for c in lang_data.values()) for l in all_langs}
top_langs=[l for l,_ in sorted(lang_totals.items(),key=lambda x:-x[1])[:15]]

scenarios=sorted(lang_data.keys())
matrix=np.zeros((len(scenarios),len(top_langs)))
for i,sc in enumerate(scenarios):
    for j,lg in enumerate(top_langs):
        matrix[i,j]=lang_data[sc].get(lg,0)

fig,ax=plt.subplots(figsize=(14,8))
sns.heatmap(matrix,xticklabels=top_langs,yticklabels=scenarios,annot=True,fmt='g',
            cmap='Blues',cbar_kws={'label':'Number of GPTs'},linewidths=0.5,ax=ax)
ax.set_xlabel('Language',fontsize=12,fontweight='bold')
ax.set_ylabel('Forbidden Scenario',fontsize=12,fontweight='bold')
ax.set_title('Figure 6: Language statistics of misused GPTs.',fontsize=14,fontweight='bold',pad=20)
plt.xticks(rotation=45,ha='right');plt.yticks(rotation=0);plt.tight_layout()
plt.savefig(f"{output_dir}/figure6.png",dpi=300,bbox_inches='tight')

print(f"\n{'='*60}")
print("✅ Complete!")
print(f"{'='*60}")
print(f"\nOutputs:")
print(f"  {output_dir}/table1.csv")
print(f"  {output_dir}/figure6.png")
print(f"  {output_dir}/scenario_*.csv ({len(results)} files)")