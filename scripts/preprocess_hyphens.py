# remove hyphen + space syllable breaks like "konuşma- lar" only when both
# sides are alphabetic letters (keeps structures such as "1 -" untouched).
import argparse
import re
import sys
from pathlib import Path

# to run : python3 scripts/preprocess_hyphens.py TXTS_deepseek

LETTER_CHARS = "A-Za-zÇĞİÖŞÜÂÎÛçğıöşüâîû"
HYPHEN_SPLIT_PATTERN = re.compile(
    rf"(?<=[{LETTER_CHARS}])-\s*(?=[{LETTER_CHARS}])"
)


def remove_hyphens(text: str) -> str:
    """Collapse layout hyphenation when surrounded by letters."""
    return HYPHEN_SPLIT_PATTERN.sub("", text)


def process_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    transformed = remove_hyphens(original)
    if transformed != original:
        path.write_text(transformed, encoding="utf-8")


def iter_mmd_files(root: Path):
    if root.is_file() and root.suffix == ".mmd":
        yield root
        return
    # Look for result.mmd files recursively
    for file_path in root.rglob("result.mmd"):
        if file_path.is_file():
            yield file_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Remove hyphen+space syllable breaks from result.mmd files. "
            "Provide a directory (e.g. TXTS_deepseek) to process all result.mmd files recursively. "
            "If no path is supplied, the script reads from stdin and writes to stdout."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="/Users/wbagger/Documents/Semantic-Analysis-of-TBMM-Transcripts/data/TXTS_deepseek",
        help="Directory to process all result.mmd files recursively, or a single .mmd file (optional).",
    )
    args = parser.parse_args()

    if args.path:
        root = Path(args.path).expanduser().resolve()
        if not root.exists():
            parser.error(f"{root} does not exist")
        count = 0
        for file_path in iter_mmd_files(root):
            process_file(file_path)
            count += 1
            if count % 10 == 0:
                print(f"Processed {count} result.mmd files...")
        print(f"\n✅ Processed {count} result.mmd file(s) under {root}")
    else:
        for line in sys.stdin:
            sys.stdout.write(remove_hyphens(line))


if __name__ == "__main__":
    main()

