# repair_json.py
# Created on: 2025-11-23 19:58:30
# Author: VuLe@macbook
# Last updated: 2025-11-23 19:58:33
# Last modified by: VuLe@macbook

"""
JSON Repair Utility for Corrupted GPT Data Files

This script attempts to repair corrupted JSON files that may have been
interrupted during writing. It can:
1. Detect where corruption occurs
2. Truncate to last valid entry
3. Create a backup before repair
4. Validate the repaired JSON
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime


def find_last_valid_entry(file_path: str):
    """
    Find the last valid complete JSON entry in a corrupted file.
    
    Strategy:
    1. Read file content
    2. Find all occurrences of complete GPT objects
    3. Return position of last valid object
    """
    print(f"Analyzing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, None
    
    print(f"File size: {len(content):,} characters")
    
    # Try to parse as-is first
    try:
        data = json.loads(content)
        print("✅ File is valid JSON! No repair needed.")
        return content, data
    except json.JSONDecodeError as e:
        print(f"❌ JSON Error at line {e.lineno}, column {e.colno}, char {e.pos}")
        print(f"   Error: {e.msg}")
        
        # Find the error position
        error_pos = e.pos
        
        # Strategy: Look backward from error position to find last complete object
        # A complete GPT object typically ends with: }},\n or }}\n]
        
        # Find all positions where we have complete object closures
        search_back = content[:error_pos]
        
        # Look for patterns that indicate end of a complete GPT entry
        patterns = [
            '},\n  {',  # Between two objects
            '}\n  ]',   # Before array close
            '}}\n]',    # End of array
        ]
        
        last_valid_pos = -1
        
        # Find the last occurrence of a complete object separator
        for i in range(len(search_back) - 1, -1, -1):
            if search_back[i:i+4] == '},\n ':
                last_valid_pos = i + 1  # Include the comma
                break
        
        if last_valid_pos == -1:
            print("❌ Could not find any valid entry separation")
            return None, None
        
        print(f"✓ Found last valid separator at position {last_valid_pos}")
        
        # Truncate to last valid position and close the array
        truncated = search_back[:last_valid_pos]
        
        # Remove trailing comma if present
        truncated = truncated.rstrip()
        if truncated.endswith(','):
            truncated = truncated[:-1]
        
        # Ensure array is properly closed
        if not truncated.endswith(']'):
            truncated += '\n]'
        
        # Try to parse the truncated version
        try:
            data = json.loads(truncated)
            print(f"✅ Repaired JSON is valid!")
            print(f"   Original entries: ???")
            print(f"   Recovered entries: {len(data)}")
            return truncated, data
        except json.JSONDecodeError as e2:
            print(f"❌ Truncated version still invalid: {e2}")
            return None, None


def repair_json_file(input_file: str, output_file: str = None, backup: bool = True):
    """
    Repair a corrupted JSON file.
    
    Args:
        input_file: Path to corrupted JSON file
        output_file: Path to save repaired file (default: input_file with _repaired suffix)
        backup: Whether to create backup of original
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"❌ File not found: {input_file}")
        return False
    
    # Create backup
    if backup:
        backup_path = input_path.with_suffix('.json.backup')
        print(f"Creating backup: {backup_path}")
        try:
            with open(input_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"✅ Backup created: {backup_path}")
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    # Repair
    repaired_content, repaired_data = find_last_valid_entry(input_file)
    
    if repaired_content is None:
        print("❌ Could not repair file")
        return False
    
    # Determine output path
    if output_file is None:
        output_path = input_path.with_name(f"{input_path.stem}_repaired.json")
    else:
        output_path = Path(output_file)
    
    # Save repaired version
    print(f"\nSaving repaired version to: {output_path}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(repaired_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Repaired file saved!")
        print(f"   Location: {output_path}")
        print(f"   Entries: {len(repaired_data)}")
        
        # Calculate how much was lost
        try:
            original_size = input_path.stat().st_size
            repaired_size = output_path.stat().st_size
            loss_pct = ((original_size - repaired_size) / original_size) * 100
            print(f"   Size: {repaired_size:,} bytes (lost {loss_pct:.1f}% of original)")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save repaired file: {e}")
        return False


def validate_json_file(file_path: str):
    """Validate a JSON file and show statistics"""
    print(f"Validating: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Valid JSON")
        print(f"   Total entries: {len(data)}")
        
        if len(data) > 0:
            # Count entries with descriptions
            with_desc = sum(
                1 for g in data 
                if g.get("gizmo", {}).get("display", {}).get("description")
            )
            print(f"   With description: {with_desc} ({with_desc/len(data)*100:.1f}%)")
            
            # Count by status
            available = sum(1 for g in data if g.get("status") == "available")
            print(f"   Available: {available}")
            
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON")
        print(f"   Error at line {e.lineno}, column {e.colno}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Repair corrupted GPT data JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Validate a JSON file
  python repair_json.py --validate data/all_2025-11-18-full.json
  
  # Repair a corrupted file
  python repair_json.py --repair data/all_2025-11-18-full.json
  
  # Repair and specify output location
  python repair_json.py --repair data/all_2025-11-18-full.json --output data/all_repaired.json
  
  # Repair without creating backup
  python repair_json.py --repair data/all_2025-11-18-full.json --no-backup

WHAT IT DOES:
  - Detects JSON corruption (usually from interrupted writes)
  - Finds last valid GPT entry
  - Truncates file to last valid entry
  - Validates repaired JSON
  - Creates backup by default
        """
    )
    
    parser.add_argument('file', help='JSON file to check/repair')
    parser.add_argument('--repair', action='store_true', help='Repair the file')
    parser.add_argument('--validate', action='store_true', help='Just validate, no repair')
    parser.add_argument('--output', '-o', help='Output file for repaired JSON')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup')
    
    args = parser.parse_args()
    
    if not Path(args.file).exists():
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    
    print("=" * 70)
    print("JSON REPAIR UTILITY")
    print("=" * 70)
    print()
    
    if args.validate:
        success = validate_json_file(args.file)
        sys.exit(0 if success else 1)
    
    if args.repair:
        success = repair_json_file(
            args.file, 
            args.output, 
            backup=not args.no_backup
        )
        sys.exit(0 if success else 1)
    
    # Default: validate only
    success = validate_json_file(args.file)
    
    if not success:
        print("\n💡 TIP: Use --repair to attempt automatic repair")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
