"""
Clean Topic Labels in Both CSV and Elasticsearch

This script cleans topic labels in both places:
1. topic_summary.csv - groq_topic_label column
2. Elasticsearch - topic_label field

Patterns handled:
- **başlık:** Topic Name **gerekçe:** ... → Extract "Topic Name"
- ... **başlık** Topic Name" → Extract "Topic Name" (at end)
- ... **proposed Title** Topic Name → Extract "Topic Name"
- **Topic Name With Words** ... → Extract if >15 chars and >3 words

All labels >60 characters are checked and cleaned if they match a pattern.
"""

import subprocess
import sys
import os

def run_csv_cleaning():
    """Run the CSV cleaning script."""
    print("=" * 80)
    print("STEP 1: CLEANING CSV (topic_summary.csv)")
    print("=" * 80)
    
    csv_script = os.path.join(os.path.dirname(__file__), "clean_groq_topic_labels.py")
    
    if not os.path.exists(csv_script):
        print("⚠️  CSV cleaning script not found:", csv_script)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, csv_script],
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ CSV cleaning failed: {e}")
        return False


def run_elasticsearch_cleaning():
    """Run the Elasticsearch cleaning script."""
    print("\n\n")
    print("=" * 80)
    print("STEP 2: CLEANING ELASTICSEARCH (topic_label field)")
    print("=" * 80)
    
    es_script = os.path.join(os.path.dirname(__file__), "clean_elastic_topic_labels.py")
    
    if not os.path.exists(es_script):
        print("⚠️  Elasticsearch cleaning script not found:", es_script)
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, es_script],
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Elasticsearch cleaning failed: {e}")
        return False


def main():
    """Main execution function."""
    print("\n" + "🧹" * 40)
    print("COMPLETE TOPIC LABEL CLEANING")
    print("Cleans both CSV and Elasticsearch")
    print("\nPatterns cleaned:")
    print("  1. **başlık:** Topic Name **gerekçe:** ...")
    print("  2. ... **başlık** Topic Name\"")
    print("  3. ... **proposed Title** Topic Name")
    print("  4. **Topic Name With Words** ...")
    print("🧹" * 40 + "\n")
    
    csv_success = run_csv_cleaning()
    es_success = run_elasticsearch_cleaning()
    
    # Final summary
    print("\n\n")
    print("=" * 80)
    print("📊 FINAL SUMMARY")
    print("=" * 80)
    print(f"CSV Cleaning:          {'✅ Success' if csv_success else '❌ Failed'}")
    print(f"Elasticsearch Cleaning: {'✅ Success' if es_success else '❌ Failed'}")
    print("=" * 80)
    
    if csv_success and es_success:
        print("\n🎉 All topic labels cleaned successfully!")
        print("\n📌 Patterns handled:")
        print("   ✅ **başlık:** Topic Name **gerekçe:** ...")
        print("   ✅ ... **başlık** Topic Name\"")
        print("   ✅ ... **proposed Title** Topic Name")
        print("   ✅ **Topic Name With Words** ...")
        print("\n📌 Next steps:")
        print("   1. Verify CSV: Check data/topic_summary.csv")
        print("   2. Verify ES: Query Elasticsearch for cleaned labels")
        print("   3. Your API will now serve clean topic names!")
    elif csv_success and not es_success:
        print("\n⚠️  CSV cleaned but Elasticsearch failed.")
        print("   You can run: python scripts/clean_elastic_topic_labels.py")
    elif not csv_success and es_success:
        print("\n⚠️  Elasticsearch cleaned but CSV failed.")
        print("   You can run: python scripts/clean_groq_topic_labels.py")
    else:
        print("\n❌ Both cleanings failed. Check error messages above.")
    
    print("\n")


if __name__ == "__main__":
    main()
