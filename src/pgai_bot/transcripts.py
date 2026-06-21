from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_settings
from .scenarios import Scenario


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def transcript_path(call_sid: str) -> Path:
    return get_settings().transcripts_dir / f"{call_sid}.txt"


def append_line(call_sid: str, speaker: str, text: str) -> None:
    ts = _utc_now()
    clean_text = (text or "").strip()

    with transcript_path(call_sid).open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {speaker}: {clean_text}\n")


def initialize_transcript(
    call_sid: str,
    scenario: Scenario,
    from_number: str,
    to_number: str,
) -> None:
    path = transcript_path(call_sid)

    with path.open("w", encoding="utf-8") as f:
        f.write("Pretty Good AI Challenge Call Transcript\n")
        f.write("=" * 48 + "\n")
        f.write(f"Created UTC: {_utc_now()}\n")
        f.write(f"Call SID: {call_sid}\n")
        f.write(f"Scenario ID: {scenario.id}\n")
        f.write(f"Scenario title: {scenario.title}\n")
        f.write(f"Objective: {scenario.objective}\n")
        f.write(f"From: {from_number}\n")
        f.write(f"To: {to_number}\n")
        f.write("\n")

        f.write("Patient profile\n")
        f.write("-" * 48 + "\n")
        for key, value in scenario.patient_profile.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")

        f.write("Scenario details\n")
        f.write("-" * 48 + "\n")
        for key, value in scenario.details.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")

        f.write("Expected checks\n")
        f.write("-" * 48 + "\n")
        for check in scenario.expected_checks:
            f.write(f"- {check}\n")
        f.write("\n")

        f.write("Transcript\n")
        f.write("-" * 48 + "\n")


def append_recording_info(call_sid: str, recording_url: Optional[str]) -> None:
    if not recording_url:
        return

    with transcript_path(call_sid).open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write("Recording\n")
        f.write("-" * 48 + "\n")
        f.write(f"Recording URL: {recording_url}\n")


def append_note(call_sid: str, note: str) -> None:
    clean_note = (note or "").strip()
    if not clean_note:
        return

    with transcript_path(call_sid).open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write("Note\n")
        f.write("-" * 48 + "\n")
        f.write(f"{clean_note}\n")