# MP Name Normalization - Configuration Update

**Date**: December 15, 2025  
**Changes**: Semicolon support + Threshold adjustment

---

## Changes Made

### 1. Added Semicolon (;) Splitting ✅

**Previous behavior**: Only split on apostrophes and commas
**New behavior**: Also split on semicolons

```python
# Before
name = re.split(r"[,]", name)[0]

# After  
name = re.split(r"[,;]", name)[0]
```

**Examples**:
- `"Mehmet Ali; description"` → `"Mehmet Ali"`
- `"Name, text; more"` → `"Name"`

---

### 2. Lowered Long Name Threshold: 70 → 45 chars ✅

**Previous threshold**: 70 characters  
**New threshold**: 45 characters

This makes detection more aggressive for catching extraction errors where extra text gets concatenated to names.

**Impact**:
- Names with 46+ characters are now flagged as problematic
- Better detection of compound/concatenated names
- More entries will trigger fuzzy matching to find correct shorter variants

---

### 3. Fixed Critical Apostrophe Bug (U+2019) 🐛✅

**Issue Found**: The regex pattern only matched regular apostrophes (`'` U+0027), but many entries in the CSV contained RIGHT SINGLE QUOTATION MARK (`'` U+2019).

**Fix**: Updated pattern to handle multiple apostrophe types

```python
# Before (BROKEN)
name = re.split(r"['']", name)[0]  # Both characters were U+0027

# After (FIXED)
name = re.split(r"['\u2019'\u201B`]", name)[0]
```

**Supported characters**:
- `'` U+0027 (APOSTROPHE)
- `'` U+2019 (RIGHT SINGLE QUOTATION MARK) ← **Was missing!**
- `‛` U+201B (SINGLE HIGH-REVERSED-9 QUOTATION MARK)
- `` ` `` U+0060 (GRAVE ACCENT)

**Impact**: This bug fix alone improved deduplication from 20.4% → 27.4% reduction!

---

## Files Modified

### Core Module
**`src/mp_name_normalizer.py`**
- `normalize_mp_name()`: Added semicolon + fixed apostrophe pattern
- `is_valid_name_length()`: Changed default from 70 → 45

### Deduplication Script
**`scripts/deduplicate_mp_lookup.py`**
- `identify_problematic_names()`: Changed max_length from 70 → 45
- Updated display message to show ">45 chars"

### Extraction Scripts
**`src/aciklamalar_d17-d22.py`**
- Updated `max_length` parameter from 70 → 45

**`src/aciklamalar_d25-d28.py`**
- Updated `max_length` parameter from 70 → 45

---

## Results

### Before All Fixes
```
Original entries:     1,917
Deduplicated:         1,525
Reduction:            20.4%
Problematic (>70):      256
Ahmet Yıldırım:           8
```

### After Apostrophe Fix (U+2019)
```
Original entries:     1,917
Deduplicated:         1,391
Reduction:            27.4%  (+7%)
Problematic (>70):        1  (-255!)
Ahmet Yıldırım:           1  ✅ FIXED
```

### After Threshold Change (70 → 45)
```
Running on already-clean data (1,484 entries):
Problematic (>45):       18  (detected more edge cases)
Additional merges:       75
Final count:          1,409
```

---

## Testing Results

### Semicolon Splitting ✅
```python
normalize_mp_name("Mehmet Ali; description")
# Result: "Mehmet Ali"
```

### Comma Splitting (still works) ✅
```python
normalize_mp_name("Ahmet Yılmaz, extra info")
# Result: "Ahmet Yılmaz"
```

### U+2019 Apostrophe (FIXED!) ✅
```python
normalize_mp_name("Name'in açıklaması")  # Contains U+2019
# Result: "Name"
```

### Combined Separators ✅
```python
normalize_mp_name("Person'in, text; more")
# Result: "Person"
```

### New 45-Char Threshold ✅
```python
is_valid_name_length("A" * 44, 45)  # True
is_valid_name_length("A" * 45, 45)  # True
is_valid_name_length("A" * 46, 45)  # False ← flagged as problematic
```

---

## Usage in Extraction Pipeline

When extracting speeches, MP names are now processed as follows:

1. **Extract raw name** from document
2. **Split on apostrophes**: `'` `'` `‛` `` ` ``
3. **Split on separators**: `,` `;`
4. **Trim whitespace**
5. **Validate length**: Must be ≤ 45 chars
6. **If too long**: Find matching shorter name via fuzzy match (~90%)
7. **Look up** in cleaned `mp_lookup.csv`

---

## Example Transformation

**Before normalization**:
```
Ahmet Yıldırım'ın sataşma nedeniyle yaptığı konuşmasındaki bazı 
ifadelerine ilişkin açıklaması 189:190 25.- Muş Milletvekili Ahmet Yıldırım
```
(139 characters - contains U+2019 apostrophe)

**After normalization**:
```
Ahmet Yıldırım
```
(14 characters)

**Result**: This entry and 7 other variants all map to the same canonical name!

---

## Configuration Constants

Current configuration in the system:

```python
MAX_NAME_LENGTH = 45  # Characters
FUZZY_MATCH_THRESHOLD = 0.9  # 90% similarity
APOSTROPHE_PATTERN = r"['\u2019'\u201B`]"
SEPARATOR_PATTERN = r"[,;]"
```

---

## Future Considerations

Potential additional improvements:
- [ ] Add parentheses `()` stripping: `"Name (additional info)"` → `"Name"`
- [ ] Add hyphen handling for compound names
- [ ] Configurable threshold via environment variable
- [ ] Add Turkish-specific character normalization
- [ ] Machine learning for name entity recognition

---

## Backward Compatibility

✅ All changes are backward compatible
✅ Old extraction runs will benefit from re-running deduplication
✅ No breaking changes to API or file formats
✅ Existing `mp_lookup.csv` can be safely re-deduplicated

---

## Credits

**Apostrophe bug discovered by**: User (Unicode U+2019 vs U+0027 detection)  
**Impact**: Fixed critical bug affecting 255+ entries

---

## Related Documentation

- [MP Name Normalization System](./mp_name_normalization.md)
- [Initial Implementation](./mp_name_normalization_update.md)
