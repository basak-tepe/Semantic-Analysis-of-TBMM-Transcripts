"""
Clean Groq Topic Labels in topic_summary.csv

This script cleans the groq_topic_label column by extracting just the topic name
from entries that contain formatting.

Patterns handled:
1. **başlık:** Topic Name **gerekçe:** ... → Extract "Topic Name"
2. ... **başlık** Topic Name" → Extract "Topic Name" (at end)
3. **Topic Name With Multiple Words** ... → Extract if >15 chars and >3 words
4. ... **proposed Title** Topic Name → Extract "Topic Name"
"""

import csv
import re
import os
from typing import List, Dict

# Paths
INPUT_FILE = "../data/topic_summary.csv"
OUTPUT_FILE = "../data/topic_summary.csv"
BACKUP_FILE = "../data/topic_summary_backup.csv"
CHARACTER_THRESHOLD = 60


def clean_topic_label(label: str) -> str:
    """
    Clean a topic label by extracting just the title.
    
    Rules:
    1. If label <= 60 characters, return as-is
    2. If contains **başlık:** (with colon), extract text until next **
    3. If contains **başlık** (no colon) at end, extract text after it
    4. If contains **proposed Title** or similar, extract text after it
    5. If starts with **, extract first word group if >15 chars and >3 words
    6. Otherwise, return as-is
    
    Args:
        label: Raw topic label
        
    Returns:
        Cleaned topic label
    """
    if not label or label.strip() == "":
        return label
    
    # Only clean if longer than threshold
    if len(label) <= CHARACTER_THRESHOLD:
        return label
    
    # Pattern 1: Check for **başlık:** pattern (with colon)
    if "**başlık:**" in label.lower() or "**baslik:**" in label.lower():
        match = re.search(
            r'\*\*(?:başlık|baslik):\*\*\s*(.+?)\s*\*\*',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            return cleaned
    
    # Pattern 2: Check for **başlık** at the end (without colon)
    # Format: ... **başlık** Topic Name" or ... **başlık** Topic Name
    if "**başlık**" in label.lower() or "**baslik**" in label.lower():
        match = re.search(
            r'\*\*(?:başlık|baslik)\*\*\s*(.+?)(?:"|$)',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            # Remove trailing quote if present
            cleaned = cleaned.rstrip('"').strip()
            if cleaned:
                return cleaned
    
    # Pattern 3: Check for **proposed Title** or similar markers
    # Format: ... **proposed Title** Topic Name
    if "**proposed" in label.lower() or "**önerilen" in label.lower():
        match = re.search(
            r'\*\*(?:proposed|önerilen)\s+(?:title|başlık)\*\*\s*(.+?)$',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            # Remove trailing quote if present
            cleaned = cleaned.rstrip('"').strip()
            if cleaned:
                return cleaned
    
    # Pattern 4: Check if starts with ** and has content
    # Format: **Some Topic Name** rest of text...
    match = re.match(r'\*\*([^*]+)\*\*', label)
    if match:
        potential_topic = match.group(1).strip()
        
        # Check criteria: >15 chars and >3 words
        word_count = len(potential_topic.split())
        char_count = len(potential_topic)
        
        if char_count > 15 and word_count > 3:
            return potential_topic
    
    # If no pattern matched, return as-is
    return label.strip()


def clean_topic_summary_csv(input_file: str, output_file: str, backup_file: str) -> Dict[str, int]:
    """
    Clean the groq_topic_label column in topic_summary.csv.
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV
        backup_file: Path to backup CSV
        
    Returns:
        Dictionary with statistics
    """
    print("=" * 80)
    print("CLEANING GROQ TOPIC LABELS (CSV)")
    print("=" * 80)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Backup: {backup_file}")
    print("=" * 80)
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        return {}
    
    # Statistics
    stats = {
        'total': 0,
        'cleaned': 0,
        'unchanged': 0,
        'empty': 0,
        'pattern1': 0,
        'pattern2': 0,
        'pattern3': 0,
        'pattern4': 0
    }
    
    cleaned_examples = []
    
    try:
        # Read all data
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # Create backup
        import shutil
        shutil.copy2(input_file, backup_file)
        print(f"✅ Created backup: {backup_file}\n")
        
        # Process each row
        for row in rows:
            stats['total'] += 1
            original_label = row.get('groq_topic_label', '')
            
            if not original_label or original_label.strip() == "":
                stats['empty'] += 1
                continue
            
            cleaned_label = clean_topic_label(original_label)
            
            # Check if changed
            if original_label != cleaned_label:
                stats['cleaned'] += 1
                
                # Detect pattern
                if "**başlık:**" in original_label.lower() or "**baslik:**" in original_label.lower():
                    stats['pattern1'] += 1
                    pattern = "Pattern 1 (**başlık:**)"
                elif ("**başlık**" in original_label.lower() or "**baslik**" in original_label.lower()) and \
                     ("**başlık:**" not in original_label.lower() and "**baslik:**" not in original_label.lower()):
                    stats['pattern2'] += 1
                    pattern = "Pattern 2 (**başlık** at end)"
                elif "**proposed" in original_label.lower() or "**önerilen" in original_label.lower():
                    stats['pattern3'] += 1
                    pattern = "Pattern 3 (**proposed Title**)"
                elif original_label.startswith("**"):
                    stats['pattern4'] += 1
                    pattern = "Pattern 4 (**Topic**)"
                else:
                    pattern = "Unknown"
                
                # Save first 10 examples
                if len(cleaned_examples) < 10:
                    cleaned_examples.append({
                        'original': original_label[:100] + "..." if len(original_label) > 100 else original_label,
                        'cleaned': cleaned_label,
                        'pattern': pattern
                    })
                
                # Update row
                row['groq_topic_label'] = cleaned_label
            else:
                stats['unchanged'] += 1
        
        # Write cleaned data
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"📊 Statistics:")
        print(f"   Total rows: {stats['total']:,}")
        print(f"   🔧 Cleaned: {stats['cleaned']:,}")
        print(f"      • Pattern 1 (**başlık:** ...): {stats['pattern1']:,}")
        print(f"      • Pattern 2 (... **başlık** Topic): {stats['pattern2']:,}")
        print(f"      • Pattern 3 (**proposed Title** ...): {stats['pattern3']:,}")
        print(f"      • Pattern 4 (**Topic** ...): {stats['pattern4']:,}")
        print(f"   ✓ Unchanged: {stats['unchanged']:,}")
        print(f"   ⚠️  Empty/null: {stats['empty']:,}")
        
        if cleaned_examples:
            print(f"\n📋 Sample Cleanings:")
            for i, example in enumerate(cleaned_examples, 1):
                print(f"\n{i}. [{example['pattern']}]")
                print(f"   Original: {example['original']}")
                print(f"   Cleaned:  {example['cleaned']}")
        
        print(f"\n✅ Cleaned file saved to: {output_file}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Error cleaning data: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """Main execution function."""
    print("\n" + "🧹" * 40)
    print("GROQ TOPIC LABEL CLEANING (CSV)")
    print("🧹" * 40)
    
    stats = clean_topic_summary_csv(INPUT_FILE, OUTPUT_FILE, BACKUP_FILE)
    
    if not stats:
        print("❌ Cleaning failed.")
        return
    
    print("\n" + "=" * 80)
    print("✅ CSV CLEANING COMPLETE!")
    print("=" * 80)
    print(f"📄 Original backed up to: {BACKUP_FILE}")
    print(f"📄 Cleaned file: {OUTPUT_FILE}")
    print(f"🔧 Labels cleaned: {stats.get('cleaned', 0):,}")
    print(f"✓ Labels unchanged: {stats.get('unchanged', 0):,}")
    print("=" * 80)
    
    if stats.get('cleaned', 0) > 0:
        print(f"\n💡 The groq_topic_label column is now clean and ready to use!")


if __name__ == "__main__":
    main()
