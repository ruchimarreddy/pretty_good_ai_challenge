import argparse
import sys
import time
from typing import Iterable

from twilio.rest import Client

from .config import get_settings
from .scenarios import SCENARIOS, get_scenario


def validate_target_number(target_number: str) -> None:
    # Guardrail: challenge calls must go only to Pretty Good AI's assessment number.
    allowed = "+18054398008"
    if target_number != allowed:
        raise ValueError(f"Refusing to call {target_number}. Challenge target must be {allowed}.")


def make_call(scenario_id: str) -> str:
    settings = get_settings()
    validate_target_number(settings.target_number)
    scenario = get_scenario(scenario_id)
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    base = settings.public_base_url.rstrip("/")
    url = f"{base}/voice/start?scenario_id={scenario.id}"
    status_callback = f"{base}/voice/status"

    call = client.calls.create(
        to=settings.target_number,
        from_=settings.twilio_from_number,
        url=url,
        method="POST",
        record=True,
        recording_channels="dual",
        status_callback=status_callback,
        status_callback_method="POST",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        recording_status_callback=status_callback,
        recording_status_callback_method="POST",
    )
    print(f"Started call for scenario '{scenario.id}' — Call SID: {call.sid}")
    print(f"Scenario objective: {scenario.objective}")
    return call.sid


def run_many(scenario_ids: Iterable[str], spacing_seconds: int = 20) -> None:
    for idx, scenario_id in enumerate(scenario_ids, start=1):
        print(f"\n[{idx}] Calling scenario: {scenario_id}")
        make_call(scenario_id)
        if idx < len(list(scenario_ids)):
            print(f"Waiting {spacing_seconds} seconds before next call...")
            time.sleep(spacing_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Pretty Good AI challenge calls.")
    parser.add_argument("--scenario", help="Scenario id to run, e.g. appointment_simple")
    parser.add_argument("--all", action="store_true", help="Run all 10 scenarios")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--spacing", type=int, default=30, help="Seconds between calls when using --all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list:
        for sid, scenario in SCENARIOS.items():
            print(f"{sid}: {scenario.title}")
        return 0

    if args.all:
        scenario_ids = list(SCENARIOS.keys())
        for idx, scenario_id in enumerate(scenario_ids, start=1):
            print(f"\n[{idx}/{len(scenario_ids)}] {scenario_id}")
            make_call(scenario_id)
            if idx != len(scenario_ids):
                print(f"Waiting {args.spacing} seconds...")
                time.sleep(args.spacing)
        return 0

    if args.scenario:
        make_call(args.scenario)
        return 0

    print("Choose --scenario <id>, --all, or --list", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
