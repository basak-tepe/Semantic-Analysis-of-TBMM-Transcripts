"""
Incremental Speech Processing Pipeline

This pipeline processes new sessions from TXTs_deepseek folder, extracts speeches,
and adds only new ones to Elasticsearch.

Usage:
    python scripts/incremental_speech_pipeline.py [OPTIONS]

Options:
    --term N          : Process only specific term (17-28)
    --year N          : Process only specific year (requires --term)
    --dry-run         : Show what would be processed without making changes
    --update           : Update/replace existing speeches (default: skip existing)
"""
import os
import sys
import argparse
import glob
from typing import Dict, List, Set, Optional

# Check dependencies before proceeding
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import bulk
except ImportError as e:
    print("❌ ERROR: Missing required dependency 'elasticsearch'")
    print("   Please install it with: pip install elasticsearch")
    print(f"   Error: {e}")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError as e:
    print("❌ ERROR: Missing required dependency 'tqdm'")
    print("   Please install it with: pip install tqdm")
    print(f"   Error: {e}")
    sys.exit(1)

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Import extraction modules using importlib (handles hyphens in filenames)
import importlib.util

extract_d17_d22 = None
load_mp_lookup = None
load_date_lookup = None
save_mp_lookup = None

try:
    spec = importlib.util.spec_from_file_location(
        "aciklamalar_d17_d22",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'aciklamalar_d17-d22.py')
    )
    module_d17 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_d17)
    extract_d17_d22 = module_d17.extract_speeches_from_file
    load_mp_lookup = module_d17.load_mp_lookup
    load_date_lookup = module_d17.load_date_lookup
    save_mp_lookup = module_d17.save_mp_lookup
    print(f"✅ Successfully imported aciklamalar_d17-d22")
except Exception as e:
    print(f"❌ ERROR: Could not import aciklamalar_d17-d22: {e}")
    print(f"   Make sure all dependencies are installed (elasticsearch, etc.)")
    import traceback
    traceback.print_exc()

extract_d23_d28 = None
load_mp_lookup_d23 = None
load_date_lookup_d23 = None
save_mp_lookup_d23 = None

try:
    spec = importlib.util.spec_from_file_location(
        "aciklamalar_d23_d28",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'aciklamalar_d23-d28.py')
    )
    module_d23 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_d23)
    extract_d23_d28 = module_d23.extract_speeches_from_file
    load_mp_lookup_d23 = module_d23.load_mp_lookup
    load_date_lookup_d23 = module_d23.load_date_lookup
    save_mp_lookup_d23 = module_d23.save_mp_lookup
    print(f"✅ Successfully imported aciklamalar_d23-d28")
except Exception as e:
    print(f"❌ ERROR: Could not import aciklamalar_d23-d28: {e}")
    print(f"   Make sure all dependencies are installed (elasticsearch, etc.)")
    import traceback
    traceback.print_exc()

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
TXTS_DEEPSEEK_PATH = "TXTs_deepseek"


def scan_for_sessions(
    base_path: str = TXTS_DEEPSEEK_PATH,
    term: Optional[int] = None,
    year: Optional[int] = None
) -> List[Dict]:
    """
    Scan TXTs_deepseek folder for sessions to process.
    
    Args:
        base_path: Base path to TXTs_deepseek folder
        term: Optional term filter (17-28)
        year: Optional year filter (requires term)
        
    Returns:
        List of session dicts with term, year, filepath, and type
    """
    sessions = []
    
    # Terms 17-22 use result.mmd files in subfolders
    for t in range(17, 23):
        if term and t != term:
            continue
        
        for y in range(1, 6):
            if year and y != year:
                continue
            
            folder_path = os.path.join(base_path, f"d{t}-y{y}_TXTs")
            if not os.path.exists(folder_path):
                continue
            
            mmd_files = glob.glob(os.path.join(folder_path, "*", "result.mmd"))
            for filepath in mmd_files:
                parent_folder = os.path.basename(os.path.dirname(filepath))
                sessions.append({
                    'term': t,
                    'year': y,
                    'filepath': filepath,
                    'parent_folder': parent_folder,
                    'type': 'd17-d22'
                })
    
    # Terms 23-28 use .txt files directly
    for t in range(23, 29):
        if term and t != term:
            continue
        
        years_map = {
            23: [1, 2, 3, 4, 5],
            24: [1, 2, 3],
            25: [1, 2],
            26: [1, 2, 3],
            27: [1, 2, 3, 4, 5, 6],
            28: [1]
        }
        
        for y in years_map.get(t, []):
            if year and y != year:
                continue
            
            folder_path = os.path.join(base_path, f"d{t}-y{y}_txts")
            if not os.path.exists(folder_path):
                continue
            
            txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
            for filepath in txt_files:
                if filepath.endswith(("fih.txt", "gnd.txt")):
                    continue
                
                sessions.append({
                    'term': t,
                    'year': y,
                    'filepath': filepath,
                    'type': 'd23-d28'
                })
    
    return sessions


def check_existing_speeches(
    es: Elasticsearch,
    speech_ids: Set[str],
    index_name: str = ELASTICSEARCH_INDEX
) -> Set[str]:
    """
    Check which speech IDs already exist in Elasticsearch.
    
    Args:
        es: Elasticsearch client
        speech_ids: Set of speech IDs to check
        index_name: Index name
        
    Returns:
        Set of existing speech IDs
    """
    if not speech_ids:
        return set()
    
    # Use mget for efficient bulk checking
    existing_ids = set()
    ids_list = list(speech_ids)
    
    # Process in batches of 1000
    batch_size = 1000
    for i in range(0, len(ids_list), batch_size):
        batch_ids = ids_list[i:i + batch_size]
        try:
            response = es.mget(
                index=index_name,
                body={'ids': batch_ids}
            )
            
            for doc in response['docs']:
                if doc.get('found'):
                    existing_ids.add(doc['_id'])
        except Exception as e:
            print(f"⚠️  Error checking batch: {e}")
    
    return existing_ids


def extract_and_index_speeches(
    es: Elasticsearch,
    sessions: List[Dict],
    dry_run: bool = False,
    update: bool = False,
    index_name: str = ELASTICSEARCH_INDEX
) -> List[Dict]:
    """
    Extract speeches from sessions and index them.
    
    Args:
        es: Elasticsearch client
        sessions: List of session dicts
        dry_run: If True, don't actually index
        update: If True, update existing speeches; if False, skip existing ones
        index_name: Index name
        
    Returns:
        List of speech dictionaries that were indexed/updated
    """
    print("\n" + "=" * 80)
    print("Extract and Index Speeches")
    print("=" * 80)
    
    # Load MP lookup and date lookup
    print("\n📋 Loading MP lookup and date lookup...")
    if load_mp_lookup:
        load_mp_lookup()
    if load_date_lookup:
        load_date_lookup()
    if load_mp_lookup_d23:
        load_mp_lookup_d23()
    if load_date_lookup_d23:
        load_date_lookup_d23()
    
    all_speeches = []
    
    # Check if extraction functions are available
    if not extract_d17_d22 and not extract_d23_d28:
        print("\n❌ ERROR: No extraction functions available!")
        print("   Both aciklamalar_d17-d22 and aciklamalar_d23-d28 failed to import.")
        print("   Please check the error messages above and install missing dependencies.")
        return []
    
    if not extract_d17_d22:
        print("⚠️  Warning: aciklamalar_d17-d22 not available - will skip terms 17-22")
    if not extract_d23_d28:
        print("⚠️  Warning: aciklamalar_d23-d28 not available - will skip terms 23-28")
    
    # Extract speeches from all sessions
    print(f"\n📂 Extracting speeches from {len(sessions)} sessions...")
    for session in tqdm(sessions, desc="Processing sessions"):
        try:
            if session['type'] == 'd17-d22' and extract_d17_d22:
                speeches = extract_d17_d22(
                    session['filepath'],
                    session['term'],
                    session['year'],
                    session.get('parent_folder')
                )
            elif session['type'] == 'd23-d28' and extract_d23_d28:
                speeches = extract_d23_d28(
                    session['filepath'],
                    session['term'],
                    session['year']
                )
            else:
                # Skip silently in tqdm to avoid spam
                continue
            
            all_speeches.extend(speeches)
        except Exception as e:
            print(f"⚠️  Error extracting from {session['filepath']}: {e}")
            continue
    
    if not all_speeches:
        print("⚠️  No speeches extracted")
        return []
    
    print(f"✅ Extracted {len(all_speeches)} speeches")
    
    # Check which speeches already exist
    print("\n🔍 Checking for existing speeches in Elasticsearch...")
    speech_ids = {s['_id'] for s in all_speeches}
    existing_ids = check_existing_speeches(es, speech_ids, index_name)
    
    if update:
        # Include all speeches (new and existing) for update
        speeches_to_index = all_speeches
        print(f"   Total speeches: {len(all_speeches)}")
        print(f"   Already exist: {len(existing_ids)} (will be updated)")
        print(f"   New speeches: {len(all_speeches) - len(existing_ids)}")
    else:
        # Only include new speeches
        speeches_to_index = [s for s in all_speeches if s['_id'] not in existing_ids]
        print(f"   Total speeches: {len(all_speeches)}")
        print(f"   Already exist: {len(existing_ids)} (skipped)")
        print(f"   New speeches: {len(speeches_to_index)}")
    
    if not speeches_to_index:
        if update:
            print("✅ No speeches to process")
        else:
            print("✅ No new speeches to index")
        return []
    
    if dry_run:
        action_type = "update" if update else "index"
        print(f"\n🔍 DRY RUN: Would {action_type} the following speeches:")
        for s in speeches_to_index[:10]:
            status = "(existing)" if s['_id'] in existing_ids else "(new)"
            print(f"   {s['_id']} {status}: {s['speech_giver']} - {s['speech_title'][:50]}...")
        if len(speeches_to_index) > 10:
            print(f"   ... and {len(speeches_to_index) - 10} more")
        return speeches_to_index
    
    # Index/update speeches
    action_type = "Updating" if update else "Indexing"
    print(f"\n💾 {action_type} {len(speeches_to_index)} speeches...")
    actions = []
    for s in speeches_to_index:
        if update and s['_id'] in existing_ids:
            # Use update operation for existing speeches
            actions.append({
                '_op_type': 'update',
                '_index': index_name,
                '_id': s['_id'],
                'doc': {
                    k: v for k, v in s.items() if k != '_id'
                }
            })
        else:
            # Use index operation for new speeches
            actions.append({
                '_op_type': 'index',
                '_index': index_name,
                '_id': s['_id'],
                '_source': {
                    k: v for k, v in s.items() if k != '_id'
                }
            })
    
    try:
        success, failed = bulk(es, actions, stats_only=True, raise_on_error=False)
        if update:
            updated_count = len([s for s in speeches_to_index if s['_id'] in existing_ids])
            new_count = len(speeches_to_index) - updated_count
            print(f"✅ Processed {success} speeches ({new_count} new, {updated_count} updated)")
        else:
            print(f"✅ Indexed {success} speeches")
        if failed:
            print(f"⚠️  Failed to process {failed} speeches")
    except Exception as e:
        print(f"❌ Error processing speeches: {e}")
        return []
    
    # Save MP lookup
    if save_mp_lookup:
        save_mp_lookup()
    if save_mp_lookup_d23:
        save_mp_lookup_d23()
    
    return speeches_to_index




def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Incremental Speech Processing Pipeline"
    )
    parser.add_argument(
        '--term',
        type=int,
        choices=range(17, 29),
        help='Process only specific term (17-28)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Process only specific year (requires --term)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without making changes'
    )
    parser.add_argument(
        '--update',
        action='store_true',
        help='Update/replace existing speeches (default: skip existing ones)'
    )
    parser.add_argument(
        '--txts-path',
        type=str,
        default=TXTS_DEEPSEEK_PATH,
        help=f'Path to TXTs_deepseek folder (default: {TXTS_DEEPSEEK_PATH})'
    )
    
    args = parser.parse_args()
    
    if args.year and not args.term:
        parser.error("--year requires --term")
    
    print("=" * 80)
    print("INCREMENTAL SPEECH PROCESSING PIPELINE")
    print("=" * 80)
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    if args.update:
        print("🔄 UPDATE MODE - Existing speeches will be replaced")
    print()
    
    # Connect to Elasticsearch
    print("🔌 Connecting to Elasticsearch...")
    try:
        es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        if not es.ping():
            raise Exception("Ping failed")
        print(f"✅ Connected to {ELASTICSEARCH_HOST}")
    except Exception as e:
        print(f"❌ Failed to connect to Elasticsearch: {e}")
        sys.exit(1)
    
    # Scan for sessions
    print(f"\n📂 Scanning for sessions in {args.txts_path}...")
    sessions = scan_for_sessions(args.txts_path, args.term, args.year)
    
    if not sessions:
        print("⚠️  No sessions found")
        sys.exit(0)
    
    print(f"✅ Found {len(sessions)} sessions to process")
    
    # Extract and index speeches
    speeches = extract_and_index_speeches(es, sessions, args.dry_run, args.update)
    
    print("\n" + "=" * 80)
    if speeches:
        if args.update:
            print(f"✅ PIPELINE COMPLETE - Processed {len(speeches)} speeches")
        else:
            print(f"✅ PIPELINE COMPLETE - Indexed {len(speeches)} new speeches")
    else:
        if args.update:
            print("✅ PIPELINE COMPLETE - No speeches to process")
        else:
            print("✅ PIPELINE COMPLETE - No new speeches to index")
    print("=" * 80)


if __name__ == "__main__":
    main()

