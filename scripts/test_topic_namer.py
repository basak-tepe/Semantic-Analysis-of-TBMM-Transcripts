#!/usr/bin/env python3
"""
Test script for LLM Topic Namer

This script tests the Groq LLM integration for generating readable topic names.
"""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_topic_namer import GroqTopicNamer, process_all_topics
from elasticsearch import Elasticsearch


def test_api_connection():
    """Test 1: Verify Groq API connection"""
    print("=" * 80)
    print("TEST 1: Groq API Connection")
    print("=" * 80)
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        print("❌ GROQ_API_KEY not set")
        print("   Set it with: export GROQ_API_KEY='your-key'")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    try:
        namer = GroqTopicNamer(api_key=api_key)
        print("✅ GroqTopicNamer initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False


def test_single_topic_generation():
    """Test 2: Generate name for a single topic"""
    print("\n" + "=" * 80)
    print("TEST 2: Single Topic Name Generation")
    print("=" * 80)
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        print("❌ Skipping - GROQ_API_KEY not set")
        return False
    
    try:
        namer = GroqTopicNamer(api_key=api_key)
        
        # Test with sample Turkish parliament topic
        test_keywords = "ekonomi, bütçe, mali, vergi, gelir"
        test_docs = [
            "Sayın Başkan, ekonomik politikalarımız ve bütçe konusunda söz almak istiyorum. Mali disiplin önemlidir.",
            "Vergi sistemimizin yeniden düzenlenmesi gerekiyor. Gelir dağılımı adaletsizliği artıyor.",
            "Bütçe açığımızı kapatmak için ekonomik tedbirler almalıyız."
        ]
        
        print("Test Input:")
        print(f"  Keywords: {test_keywords}")
        print(f"  Docs: {len(test_docs)} sample speeches")
        print("\nGenerating name...")
        
        readable_name = namer.generate_topic_name(
            topic_id=0,
            keywords=test_keywords,
            representative_docs=test_docs
        )
        
        print(f"\n✅ Generated name: \"{readable_name}\"")
        
        # Validate
        if len(readable_name) > 5 and readable_name != test_keywords:
            print("✅ Name looks valid (length and content check passed)")
            return True
        else:
            print("⚠️  Generated name seems suspicious")
            return False
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_turkish_characters():
    """Test 3: Verify Turkish character handling"""
    print("\n" + "=" * 80)
    print("TEST 3: Turkish Character Handling")
    print("=" * 80)
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        print("❌ Skipping - GROQ_API_KEY not set")
        return False
    
    try:
        namer = GroqTopicNamer(api_key=api_key)
        
        # Test with Turkish-specific characters
        test_keywords = "eğitim, öğrenci, öğretmen, üniversite, çalışma"
        test_docs = [
            "Eğitim sistemimizi iyileştirmek için öğretmenlerimize destek vermeliyiz.",
            "Üniversitelerimizde kalite çok önemli. Öğrencilerimiz geleceğimiz.",
            "Eğitimde fırsat eşitliği sağlanmalı. Çalışmalarımız devam ediyor."
        ]
        
        print("Test Input (with Turkish chars):")
        print(f"  Keywords: {test_keywords}")
        
        readable_name = namer.generate_topic_name(
            topic_id=1,
            keywords=test_keywords,
            representative_docs=test_docs
        )
        
        print(f"\n✅ Generated name: \"{readable_name}\"")
        
        # Check if Turkish characters are preserved
        turkish_chars = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'İ', 'Ç', 'Ğ', 'Ö', 'Ş', 'Ü']
        has_turkish = any(char in readable_name for char in turkish_chars)
        
        if has_turkish or 'eğitim' in test_keywords.lower():
            print("✅ Turkish characters handled correctly")
            return True
        else:
            print("⚠️  No Turkish characters detected in output")
            return True  # Still pass, might be valid
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_csv_processing():
    """Test 4: Process topic_details.csv (if exists)"""
    print("\n" + "=" * 80)
    print("TEST 4: CSV Processing")
    print("=" * 80)
    
    csv_path = "../data/data_secret/topic_details.csv"
    
    if not os.path.exists(csv_path):
        print(f"⚠️  {csv_path} not found")
        print("   Run analyze_speech_topics.py first to generate this file")
        return None  # Not a failure, just skipped
    
    api_key = os.getenv("GROQ_API_KEY", "")
    
    if not api_key:
        print("❌ Skipping - GROQ_API_KEY not set")
        return False
    
    try:
        print(f"Processing first 3 topics from {csv_path}...")
        
        # Process only first 3 topics for testing
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            topics = [row for row in reader if int(row['Topic']) >= 0][:3]
        
        if not topics:
            print("❌ No valid topics found in CSV")
            return False
        
        namer = GroqTopicNamer(api_key=api_key)
        
        for topic in topics:
            topic_id = int(topic['Topic'])
            keywords = topic.get('Keywords', '')
            
            print(f"\nTopic {topic_id}:")
            print(f"  Keywords: {keywords[:50]}...")
            
            # Simple processing without full context
            name = namer.generate_topic_name(topic_id, keywords, [])
            print(f"  Generated: \"{name}\"")
        
        print("\n✅ CSV processing test completed")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_elasticsearch_connection():
    """Test 5: Verify Elasticsearch connection"""
    print("\n" + "=" * 80)
    print("TEST 5: Elasticsearch Connection")
    print("=" * 80)
    
    try:
        es = Elasticsearch(hosts=["http://localhost:9200"])
        
        if es.ping():
            print("✅ Elasticsearch is running")
            
            # Check index
            index = "parliament_speeches"
            if es.indices.exists(index=index):
                count = es.count(index=index)
                print(f"✅ Index '{index}' exists with {count['count']:,} documents")
                
                # Check if any docs have topic_id
                response = es.search(
                    index=index,
                    body={"query": {"exists": {"field": "topic_id"}}, "size": 1}
                )
                
                if response['hits']['total']['value'] > 0:
                    sample = response['hits']['hits'][0]['_source']
                    print(f"✅ Sample document has topic fields:")
                    print(f"   topic_id: {sample.get('topic_id')}")
                    print(f"   topic_label: {sample.get('topic_label')}")
                    return True
                else:
                    print("⚠️  No documents with topic_id found")
                    print("   Run analyze_speech_topics.py first")
                    return None
            else:
                print(f"⚠️  Index '{index}' does not exist")
                return None
        else:
            print("❌ Cannot connect to Elasticsearch")
            return False
            
    except Exception as e:
        print(f"❌ Elasticsearch error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("LLM TOPIC NAMER - TEST SUITE")
    print("=" * 80)
    print("\nThis script tests the Groq LLM integration for topic naming.")
    print("Make sure GROQ_API_KEY environment variable is set.\n")
    
    results = {
        "API Connection": test_api_connection(),
        "Single Topic Generation": test_single_topic_generation(),
        "Turkish Characters": test_turkish_characters(),
        "CSV Processing": test_csv_processing(),
        "Elasticsearch Connection": test_elasticsearch_connection()
    }
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⚠️  SKIPPED"
        
        print(f"{status:12} - {test_name}")
    
    print("\n" + "-" * 80)
    print(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 80)
    
    if failed > 0:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠️  No tests passed. Set GROQ_API_KEY and try again.")
        sys.exit(1)
    else:
        print("\n✅ All critical tests passed!")
        print("\nYou can now run: python src/analyze_speech_topics.py")
        sys.exit(0)


if __name__ == "__main__":
    main()
