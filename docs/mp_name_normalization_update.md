# MP Name Normalization - Update Log

## Update: December 15, 2025

### Changes Made

Added two enhancements to the normalization system:

1. **Comma-based splitting**: Now splits on commas (`,`) in addition to apostrophes (`'`)
2. **Party data prioritization**: When multiple matches exist, prefer names with party data

### Updated Functions

#### `normalize_mp_name()`
Now splits on both apostrophes AND commas:

```python
# Before
name = re.split(r"['']", name)[0]  # Only apostrophes

# After
name = re.split(r"['']", name)[0]  # Apostrophes first
name = name.split(',')[0]          # Then commas
```

**Examples:**
- `"Ahmet Yılmaz, additional text"` → `"Ahmet Yılmaz"`
- `"John Doe'nın, some text"` → `"John Doe"`

#### `find_similar_names()`
Added `lookup_data` parameter to prioritize matches with party information:

```python
# New parameter
lookup_data: Optional[Dict[str, Dict]] = None
```

**Sorting behavior:**
1. Similarity score (highest first)
2. Has party data (True before False)

This means a name with complete party data will be preferred over one without, even if similarity is equal.

### Re-run Results

After implementing these changes:

```
Original entries:     1,917
Deduplicated entries: 1,525
Duplicates removed:   392
Reduction:            20.4%
```

**Improvements over previous run:**
- **41 fewer problematic names** (297 → 256) thanks to comma splitting
- **26 more entries removed** (366 → 392 duplicates found)
- **Better canonical name selection** with party data prioritization

### Examples of Comma-based Cleanup

Names that were likely fixed by comma splitting:

```
Before normalization (with comma):
- "Name, additional context text"
- "MP Name, speech description"

After normalization:
- "Name"
- "MP Name"
```

These would then properly match with existing shorter variants in the lookup table.

### Party Data Prioritization Examples

When fuzzy matching finds multiple candidates:

**Scenario:** Looking for match to "Ahmet Yılmazz" (typo)

**Candidates:**
1. `"Ahmet Yılmaz"` - Has party: "AK Parti", terms: [25, 26]
2. `"Ahmet Yilmaz"` - No party, no terms

**Result:** System prefers candidate #1 because it has party data, ensuring the most complete information is retained.

### Technical Implementation

**In `src/mp_name_normalizer.py`:**
- Updated `normalize_mp_name()` to split on commas
- Updated `find_similar_names()` signature to accept `lookup_data`
- Updated `group_similar_names()` to pass `lookup_data` through

**In extraction scripts:**
- `src/aciklamalar_d17-d22.py`: Updated to pass `lookup_data=mp_lookup`
- `src/aciklamalar_d25-d28.py`: Updated to pass `lookup_data=mp_lookup`

### Backward Compatibility

- All changes are backward compatible
- `lookup_data` parameter is optional (defaults to `None`)
- Without `lookup_data`, system still works but doesn't prioritize by party data
- Comma splitting is always active and doesn't break existing functionality

### Testing Performed

✅ Apostrophe removal (existing functionality)
✅ Comma splitting (new)
✅ Combined apostrophe + comma (new)
✅ Party data prioritization (new)
✅ Backward compatibility without lookup_data (new)
✅ All Python files compile successfully
✅ Full deduplication run with improved results

### Files Modified

1. `src/mp_name_normalizer.py` - Core normalization logic
2. `src/aciklamalar_d17-d22.py` - Updated function calls
3. `src/aciklamalar_d25-d28.py` - Updated function calls

### Usage

No changes required for users - the system automatically uses the new features.

To re-run deduplication with updated logic:

```bash
# Restore original backup if needed
cp mp_lookup_backup.csv mp_lookup.csv

# Run with new logic
python3 scripts/deduplicate_mp_lookup.py
```

### Known Edge Cases

The comma splitting handles:
- Names with commas followed by descriptive text
- Names with both apostrophes and commas
- Multiple commas (takes first part)

**Important:** CSV commas in party/terms columns are not affected because we split the `speech_giver` field before CSV parsing extracts the value.

### Future Considerations

Potential improvements:
- [ ] Add semicolon (`;`) splitting if similar patterns emerge
- [ ] Add parentheses `()` stripping for text like "Name (additional info)"
- [ ] Implement weighted scoring for party data quality (some parties vs. full history)
- [ ] Add configurable separator list via config file

---

## Original Implementation: December 15, 2025

See [`mp_name_normalization.md`](./mp_name_normalization.md) for full system documentation.
