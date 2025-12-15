# MP Name Normalization System

## Overview

This system prevents MP name duplicates caused by extraction inconsistencies (apostrophes, spelling variations, etc.) through a two-phase approach:

1. **Phase 1**: One-time cleanup of existing `mp_lookup.csv`
2. **Phase 2**: Runtime normalization during speech extraction

## Files Created

### 1. Core Module
- **`src/mp_name_normalizer.py`**: Reusable normalization functions
  - `normalize_mp_name()`: Remove apostrophes and clean whitespace
  - `is_valid_name_length()`: Detect suspiciously long names (>70 chars)
  - `find_similar_names()`: Fuzzy matching with ~90% similarity threshold
  - `select_canonical_name()`: Choose best name from duplicates
  - `merge_mp_data()`: Combine data from duplicate entries

### 2. Cleanup Script
- **`scripts/deduplicate_mp_lookup.py`**: One-time deduplication script

### 3. Output Files
- **`mp_lookup.csv`**: Cleaned, deduplicated lookup table (1,552 entries)
- **`mp_lookup_backup.csv`**: Original backup before cleanup (2,885 entries)
- **`mp_deduplication_log.csv`**: Detailed merge log (1,191 operations)

## Deduplication Results

```
Original entries:     2,885
Deduplicated entries: 1,552
Duplicates removed:   1,333
Reduction:            46.2%
```

### Key Achievements
- **497 names** normalized by apostrophe removal
- **121 groups** of similar names merged using fuzzy matching
- **297 problematic names** (>70 chars) identified

## How It Works

### Normalization Process

1. **Apostrophe Removal**
   - `"Ahmet Yılmaz'ın"` → `"Ahmet Yılmaz"`
   - `"John Doe'"` → `"John Doe"`

2. **Length Validation**
   - Names >70 characters flagged as extraction errors
   - Long names matched to shorter variants via first 3 words

3. **Fuzzy Matching**
   - Finds similar names with ~90% similarity
   - Examples:
     - `"John Kernel"` ↔ `"John Kernell"`
     - `"Ahmet Yılmaz"` ↔ `"Ahmet Yilmaz"` (accent variations)

4. **Data Merging**
   - Selects variant with most complete data (party, terms)
   - Merges all unique term information
   - Uses shortest name as tiebreaker

### Runtime Integration

Both extraction scripts now use name normalization:

**`src/aciklamalar_d17-d22.py`**
**`src/aciklamalar_d25-d28.py`**

During extraction:
1. Extract raw MP name from text
2. Normalize name (remove apostrophes)
3. Check if name is valid length (<70 chars)
4. If too long, find matching shorter name using fuzzy match
5. Look up normalized name in cleaned `mp_lookup.csv`

## Usage

### Running Cleanup Again (if needed)

```bash
python3 scripts/deduplicate_mp_lookup.py
```

This will:
- Create a new backup with timestamp
- Deduplicate the current `mp_lookup.csv`
- Generate a new deduplication log

### Viewing Merge Log

```bash
# See what names were merged
head -20 mp_deduplication_log.csv

# Count merges by reason
cut -d',' -f3 mp_deduplication_log.csv | sort | uniq -c
```

### Testing Normalization

```python
from src.mp_name_normalizer import normalize_mp_name, find_similar_names

# Test apostrophe removal
name = normalize_mp_name("Mehmet Ali'nin")
print(name)  # Output: "Mehmet Ali"

# Test fuzzy matching
candidates = ["John Kernel", "Jane Doe", "Ahmet Yılmaz"]
matches = find_similar_names("John Kernell", candidates, threshold=0.9)
print(matches)  # Output: ['John Kernel']
```

## Examples from Deduplication Log

### Apostrophe Variations Merged
```
original_name                 → canonical_name
─────────────────────────────────────────────────
Enis Tütüncü'n               → Enis Tütüncü
Abdullah Karaduman'ın        → Abdullah Karaduman
```

### Spelling Variations Merged
```
original_name                 → canonical_name
─────────────────────────────────────────────────
Arsan Savaş Arpacıoğlu       → Arsan Savaş Arpaciğlu
Kamer Genc                   → Kamer Genç
M. İstemihan Talay           → M. Istemihan Talay
```

### Accent Variations Merged
```
original_name                 → canonical_name
─────────────────────────────────────────────────
Alâettin Kurt                → Alaettin Kurt
Beşer Baydar                 → Beser Baydar
```

### Long Extraction Errors
```
original_name (truncated)
─────────────────────────────────────────────────
Ali Karaoba'nın Uşak halkı adına yeni bir devlet hastanesi i... (138 chars)
Gülcan Kış, Pamukluk Barajı'na ilişkin açıklaması 50:51 14.-... (92 chars)
Engin Altay, TBMM Başkan Vekili Mustafa Şentop'a başarılar d... (478 chars)
```

These are automatically detected and mapped to shorter matching names during extraction.

## Benefits

1. **Eliminates Duplicates**: Single MPs no longer appear multiple times
2. **Consistent Lookups**: Same normalization used for cleanup and extraction
3. **Automatic Correction**: Long/malformed names auto-corrected at runtime
4. **Audit Trail**: Complete log of all merges and transformations
5. **Data Preservation**: Original data backed up, most complete data retained

## Maintenance

### When to Re-run Cleanup

Re-run deduplication if:
- New extraction runs add many new MP entries
- You notice duplicate names in search results
- Lookup table grows significantly (>2000 entries)

### Monitoring Extraction

During extraction, watch for:
- `⚠️ Mapped long name to: ...` - indicates auto-correction
- `⚠️ Could not resolve long name: ...` - may need manual review

## Technical Details

### Fuzzy Matching Algorithm

Uses `difflib.SequenceMatcher` to calculate similarity:
- Compares first 3 words of names
- Case-insensitive comparison
- Returns ratio between 0.0 (no match) and 1.0 (exact match)
- Default threshold: 0.9 (90% similarity)

### Canonical Name Selection

Priority order:
1. Most complete party data (not None/empty)
2. Most complete terms data (longest list)
3. Shortest name (tiebreaker)

Formula: `score = (party_score × 100) + (terms_count × 10) + (-name_length)`

### Data Merging

When merging variants:
- Party: Use first non-empty party found
- Terms: Union of all terms from all variants, sorted
- Canonical name: Selected using priority criteria above

## Troubleshooting

### Import Errors

If extraction scripts can't import the normalizer:

```python
# Check that both files are in the same directory
ls -la src/aciklamalar_d17-d22.py src/mp_name_normalizer.py
```

### Deduplication Fails

If cleanup script fails:

```bash
# Check if backup exists (prevents overwriting)
ls -la mp_lookup_backup.csv

# Check CSV format
head -3 mp_lookup.csv
```

### No Matches Found for Long Names

If long names aren't matched:
- Threshold might be too high (try 0.85 instead of 0.9)
- Name might not exist in lookup table
- Check deduplication log for clues

## Future Enhancements

Potential improvements:
- [ ] Add name transliteration support (Turkish ↔ ASCII)
- [ ] Implement machine learning for name entity recognition
- [ ] Add interactive review mode for uncertain merges
- [ ] Create web UI for manual deduplication review
- [ ] Add unit tests for edge cases

## Related Files

- Original implementation: `src/aciklamalar_d17-d22.py` (lines 10-18, 233-260)
- Original implementation: `src/aciklamalar_d25-d28.py` (lines 10-24, 160-190)
- MP details API: `src/get_mp_details.py`
- Session dates: `session_dates_lookup.csv`
