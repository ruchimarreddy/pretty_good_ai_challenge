"""Simple helper to scan transcripts for review cues.

This does not replace manual bug analysis. It just highlights moments worth checking.
"""
from pathlib import Path

KEYWORDS = [
    "sunday", "weekend", "emergency", "chest", "short of breath", "guarantee",
    "copay", "insurance", "refill", "password", "lab results", "not sure",
]


def main() -> None:
    transcripts_dir = Path("transcripts")
    for path in sorted(transcripts_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        hits = [kw for kw in KEYWORDS if kw in text]
        if hits:
            print(f"\n{path} — review cues: {', '.join(hits)}")
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in lines:
                if any(kw in line.lower() for kw in hits):
                    print(f"  {line[:220]}")


if __name__ == "__main__":
    main()
