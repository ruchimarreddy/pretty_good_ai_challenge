from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import requests

from .config import get_settings
from .scenarios import Scenario


SYSTEM_PROMPT = """You are PatientBot, a realistic patient calling a medical clinic AI receptionist.

You are the patient, not the clinic agent.

Return valid JSON only:
{
  "reply": "the next sentence the patient should say aloud",
  "agent_intent": "greeting | identity_request | information_request | offering_options | confirming_details | searching | handoff | task_complete | unclear",
  "goal_status": "not_started | in_progress | waiting | completed",
  "reason": "brief reason"
}

Rules:
- The reply is only what the patient says aloud.
- Use one short spoken sentence.
- Answer the clinic agent's latest question directly.
- Use only the patient profile and scenario facts.
- Sound like a normal person on the phone, not a formal script.
- It is okay to use small natural phrases like "Sure", "Okay", "Yeah", or "That works".
- Avoid overly formal wording.
- Do not invent names, dates, phone numbers, medication names, insurance plans, appointment times, or medical facts.
- If the clinic gives options, choose one option that fits the scenario facts and preferences.
- If the clinic is checking, verifying, routing, transferring, or asking the patient to hold, acknowledge and wait.
- If the clinic confirms completion, thank them and end naturally.
- Do not say goodbye until the scenario goal is clearly complete.
- If the clinic asks whether it is speaking with the wrong patient name, politely correct it.
- If the clinic says a field does not match but accepts it for demo purposes, continue with the reason for the call.
- Never mention being an AI bot, evaluator, test script, challenge participant, Twilio, transcripts, recordings, or code.
"""


def _as_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    if hasattr(value, "__dict__"):
        return dict(value.__dict__)

    return {}


def _clean_reply(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^(PatientBot|Patient|Caller)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"^The patient should say:\s*", "", text, flags=re.I)
    text = re.sub(r"^Patient response:\s*", "", text, flags=re.I)
    text = text.replace("\n", " ").strip().strip('"').strip("'")

    if len(text) > 180:
        text = text[:180].rsplit(" ", 1)[0] + "."

    return text or "Sorry, could you please repeat that?"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip().rstrip(".!?"))

def _is_recording_disclaimer(agent_text: str) -> bool:
    text = _normalize(agent_text)
    return (
        "recorded for quality" in text
        or "quality and training" in text
        or "training purposes" in text
        or "may be recorded" in text
        or "espanol" in text
        or "español" in text
        or "spanish" in text
    )
def _is_real_greeting_or_help_prompt(agent_text: str) -> bool:
    text = _normalize(agent_text)
    return (
        "thanks for calling" in text
        or "thank you for calling" in text
        or "how can i help" in text
        or "can i help" in text
        or "what can i help" in text
        or "what would you like help with" in text
    )

def _recent_patient_replies(history: List[Dict[str, str]], limit: int = 5) -> List[str]:
    replies: List[str] = []

    for turn in history[-limit:]:
        if not isinstance(turn, dict):
            continue

        reply = turn.get("PatientBot") or turn.get("patient") or turn.get("Patient") or ""
        if reply:
            replies.append(str(reply).strip())

    return replies


def _too_repetitive(candidate: str, history: List[Dict[str, str]]) -> bool:
    candidate_norm = _normalize(candidate)
    if not candidate_norm:
        return False

    recent = [_normalize(r) for r in _recent_patient_replies(history)]

    if candidate_norm in recent:
        return True

    candidate_tokens = set(candidate_norm.split())
    for prev in recent[-3:]:
        prev_tokens = set(prev.split())
        if len(candidate_tokens & prev_tokens) >= 4:
            return True

    return False


def _safe_json_loads(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {
        "reply": raw,
        "agent_intent": "unclear",
        "goal_status": "in_progress",
        "reason": "non-json model output",
    }


def _name_parts(profile: Dict[str, Any]) -> Dict[str, str]:
    full_name = str(profile.get("name", "")).strip()
    first = str(profile.get("first_name", "")).strip()
    last = str(profile.get("last_name", "")).strip()

    if not first or not last:
        parts = full_name.split()
        first = first or (parts[0] if parts else "")
        last = last or (parts[-1] if len(parts) > 1 else "")

    return {"full": full_name, "first": first, "last": last}


def _spell_name(name: str) -> str:
    words = name.upper().split()
    return ", ".join("-".join(word) for word in words)


def _agent_asked_wrong_name(agent_text: str, actual_first_name: str, actual_full_name: str) -> bool:
    text = _normalize(agent_text)

    if "speaking with" not in text and "am i speaking with" not in text:
        return False

    actual_first = _normalize(actual_first_name)
    actual_full = _normalize(actual_full_name)

    if actual_first and actual_first in text:
        return False

    if actual_full and actual_full in text:
        return False

    return True


def _is_confirmation_question(text: str) -> bool:
    confirmation_phrases = [
        "is that correct",
        "is this correct",
        "is that right",
        "is this right",
        "does that sound right",
        "can you confirm",
        "please confirm",
        "that correct",
    ]
    return any(phrase in text for phrase in confirmation_phrases) or text.strip() == "correct"


def _profile_field_reply(scenario: Scenario, agent_text: str) -> Optional[str]:
    """Generic identity/profile answerer. This avoids scenario-specific scripts."""
    text = _normalize(agent_text)

    profile = _as_dict(scenario.patient_profile)
    details = _as_dict(scenario.details)
    names = _name_parts(profile)

    full_name = names["full"]
    first_name = names["first"]
    last_name = names["last"]

    dob = (
        profile.get("date_of_birth")
        or profile.get("dob")
        or details.get("date_of_birth")
        or details.get("dob")
    )

    phone = profile.get("phone") or details.get("phone")
    phone_digits = profile.get("phone_digits") or details.get("phone_digits")
    insurance = (
        profile.get("insurance")
        or details.get("insurance")
        or details.get("insurance_plan")
    )
    insurance_state = (
        profile.get("insurance_state")
        or details.get("insurance_state")
        or details.get("state")
    )

    # If the agent says DOB/name mismatch but also asks how to help, do not repeat DOB.
    mismatch_phrases = [
        "birthday doesn't match",
        "birthday does not match",
        "date of birth doesn't match",
        "date of birth does not match",
        "doesn't match our records",
        "does not match our records",
    ]
    if any(phrase in text for phrase in mismatch_phrases):
        return None

    # Confirmation should override field extraction.
    # Example: "I have your phone number as 765-555-0512 and DOB as May 5th, is that correct?"
    if _is_confirmation_question(text):
        correction = _correct_misheard_profile_field(scenario, agent_text)
        if correction:
            return correction
        return "Yes, that's correct."

    asks_spell = "spell" in text
    asks_full_name = "full name" in text or ("first" in text and "last" in text)
    asks_last_name = "last name" in text and not asks_full_name
    asks_first_name = "first name" in text and not asks_full_name
    asks_name = "your name" in text or "speaking with" in text or "am i speaking with" in text
    asks_dob = "date of birth" in text or "birthday" in text or "birth date" in text or "dob" in text
    asks_phone = (
        "phone number" in text
        or "number on file" in text
        or "best number" in text
        or "call back" in text
        or "phone number on file" in text
    )
    asks_insurance = "insurance" in text and (
        "what" in text
        or "which" in text
        or "plan" in text
        or "do you have" in text
        or "company" in text
    )
    asks_state = (
        "what state" in text
        or "which state" in text
        or "state was issued" in text
        or "plan was issued" in text
    )

    if asks_spell and asks_full_name and full_name:
        return str(profile.get("name_spelled") or _spell_name(full_name))

    if asks_spell and asks_last_name and last_name:
        return _spell_name(last_name)

    if asks_spell and full_name:
        return str(profile.get("name_spelled") or _spell_name(full_name))

    if asks_full_name and asks_dob and full_name and dob:
        return f"My full name is {full_name}, and my date of birth is {dob}."

    if asks_last_name and last_name:
        return last_name

    if asks_first_name and first_name:
        return first_name

    # Correct "Am I speaking with Maya?" for non-Maya scenarios.
    if ("am i speaking with" in text or "speaking with" in text) and full_name:
        if _agent_asked_wrong_name(agent_text, first_name, full_name):
            return f"No, this is {full_name}."
        return f"Yes, this is {full_name}."

    if asks_name and full_name:
        return f"This is {full_name}."

    if asks_full_name and full_name:
        return f"My full name is {full_name}."

    if asks_dob and dob:
        return str(dob)

    if asks_phone and phone:
        return str(phone)

    if asks_insurance and insurance:
        return f"I have {insurance}."

    if asks_state and insurance_state:
        return f"It was issued in {insurance_state}."

    return None


def _correct_misheard_profile_field(scenario: Scenario, agent_text: str) -> Optional[str]:
    """Correct obvious repeated-back profile mismatches.

    This is generic: it compares the agent's repeated identity field with the
    scenario patient profile.
    """
    latest = _normalize(agent_text)
    profile = _as_dict(scenario.patient_profile)
    details = _as_dict(scenario.details)

    name = str(profile.get("name", "")).strip()
    first_name = str(profile.get("first_name", "")).strip()
    last_name = str(profile.get("last_name", "")).strip()
    dob = str(profile.get("date_of_birth") or profile.get("dob") or details.get("dob") or "").strip()
    phone = str(profile.get("phone") or details.get("phone") or "").strip()
    phone_digits = str(profile.get("phone_digits") or details.get("phone_digits") or "").strip()

    if ("your name as" in latest or "i have your name as" in latest) and name:
        if _normalize(name) not in latest:
            return f"Actually, my name is {name}."

    if ("first name" in latest or "last name" in latest) and name:
        if first_name and "first name" in latest and _normalize(first_name) not in latest:
            return f"Actually, my first name is {first_name}."
        if last_name and "last name" in latest and _normalize(last_name) not in latest:
            return f"Actually, my last name is {last_name}."

    # For DOB, transcripts may normalize dates differently, so only correct obvious wrong DOB mentions.
    if ("date of birth as" in latest or "birthday as" in latest) and dob:
        dob_markers = [
            _normalize(dob),
            "nineteen",
            "twenty",
            "1990",
            "1991",
            "1992",
            "1993",
            "1994",
            "1996",
            "1997",
            "1985",
            "1975",
            "1978",
            "1988",
        ]
        if not any(marker in latest for marker in dob_markers if marker):
            return f"Actually, my date of birth is {dob}."

    if ("phone number" in latest or "number as" in latest or "number at" in latest or "number of" in latest) and phone:
        # If the transcript contains only a partial number, correct it.
        if "765" in latest and phone_digits and phone_digits not in latest:
            return f"Actually, my full phone number is {phone_digits}."
        if "five five zero" in latest or "550" in latest:
            return f"Actually, my full phone number is {phone_digits or phone}."

    return None


def _goal_completed_from_agent(agent_text: str) -> bool:
    text = _normalize(agent_text)
    completion_phrases = [
        "all set",
        "you're all set",
        "you are all set",
        "confirmed",
        "scheduled",
        "booked",
        "submitted",
        "sent to",
        "routed",
        "support team will follow up",
        "clinic team will follow up",
        "request has been sent",
        "refill has been requested",
        "appointment has been canceled",
        "appointment has been cancelled",
        "has been canceled",
        "has been cancelled",
        "they'll reach out",
        "team will review it",
        "goodbye",
        "test line goodbye",
        "test line. goodbye",
    ]
    return any(phrase in text for phrase in completion_phrases)


def _agent_is_processing(agent_text: str) -> bool:
    text = _normalize(agent_text)
    processing_phrases = [
        "let me check",
        "let me verify",
        "checking",
        "verify your identity",
        "i need your",
        "please hold",
        "hold for a moment",
        "look at your record",
        "looking at your record",
        "one moment",
        "please wait",
        "stay on the line",
        "connecting you",
        "connect you",
        "representative",
        "support team",
        "clinic support",
        "route this",
        "routed",
        "i'll route",
        "i will route",
        "follow up",
        "follows up",
    ]
    return any(phrase in text for phrase in processing_phrases)


def _agent_offers_options(agent_text: str) -> bool:
    text = _normalize(agent_text)
    option_words = [
        "which one",
        "which works",
        "which would you like",
        "would you like",
        "does that work",
        "would that work",
        "openings",
        "options",
        "available",
        "i have",
    ]
    has_time = bool(
        re.search(
            r"\b(7|8|9|10|11|12|1|2|3|4|5|6)(?::\d{2})?\s*(a\.m\.|p\.m\.|am|pm)?\b",
            text,
        )
    )
    return has_time or any(word in text for word in option_words)


def _continue_phrase_for_scenario(scenario: Scenario) -> str:
    objective = _normalize(scenario.objective)

    if "cancel" in objective:
        return "Can we continue with the cancellation?"
    if "reschedule" in objective:
        return "Can we continue rescheduling the appointment?"
    if "refill" in objective or "medication" in objective or "prescription" in objective:
        return "Can we continue with the refill request?"
    if "insurance" in objective or "copay" in objective or "coverage" in objective:
        return "Can we continue with my insurance question?"
    if "location" in objective or "parking" in objective or "arrival" in objective:
        return "Can we continue with the location question?"
    if "urgent" in objective or "symptom" in objective or "chest" in objective:
        return "Can we continue with my medical concern?"
    if "appointment" in objective or "visit" in objective or "checkup" in objective:
        return "Can we continue scheduling the appointment?"

    return "Can we continue with that request?"


def _reason_for_call(scenario: Scenario) -> str:
    details = _as_dict(scenario.details)

    clarification = details.get("clarification")
    if clarification:
        return str(clarification)

    questions = details.get("questions")
    if isinstance(questions, list) and questions:
        return str(questions[0])

    reason = details.get("reason_for_call")
    if reason:
        return f"I'm calling about {reason}."

    return str(scenario.opening or scenario.objective)


def _generic_repair(
    candidate: str,
    agent_intent: str,
    goal_status: str,
    scenario: Scenario,
    history: List[Dict[str, str]],
    agent_text: str,
) -> str:
    latest = _normalize(agent_text)
    candidate_clean = _clean_reply(candidate)
    candidate_lower = _normalize(candidate_clean)

    # Hard override: if the clinic is transferring/routing/asking the patient to wait,
    # the patient should not end the call or continue asking new questions.
    if (
        "stay on the line" in latest
        or "please stay on the line" in latest
        or "connecting you" in latest
        or "connect you" in latest
        or "representative" in latest
        or "please wait" in latest
    ):
        return "Okay, I'll stay on the line."

    # If the clinic says goodbye, close instead of trying to continue.
    if "goodbye" in latest or "test line goodbye" in latest or "test line. goodbye" in latest:
        return "Thank you. Goodbye."

    # If there is an obvious repeated-back profile error, correct it.
    correction = _correct_misheard_profile_field(scenario, agent_text)
    if correction:
        return correction

    # If DOB mismatch is accepted for demo purposes and agent asks how to help,
    # continue with the scenario reason instead of repeating DOB.
    mismatch_phrases = [
        "birthday doesn't match",
        "birthday does not match",
        "date of birth doesn't match",
        "date of birth does not match",
        "doesn't match our records",
        "does not match our records",
    ]
    if any(phrase in latest for phrase in mismatch_phrases):
        if "how can i help" in latest or "can i help" in latest or "what can i help" in latest:
            return _reason_for_call(scenario)
        return f"Okay, thank you. {_continue_phrase_for_scenario(scenario)}"

    # If the agent asks how it can help, state the reason for the scenario.
    if "how can i help" in latest or "can i help" in latest or "what can i help" in latest:
        return _reason_for_call(scenario)

    # If the clinic is asking the patient to wait/hold/checking/routing, wait.
    if _agent_is_processing(agent_text):
        if "?" not in agent_text:
            return "Okay, I'll wait."
        if "bye" in candidate_lower or "goodbye" in candidate_lower:
            return "Okay, I'll wait."
        if candidate_lower == latest or candidate_lower in latest or latest in candidate_lower:
            return "Okay, I'll wait."
        if _too_repetitive(candidate_clean, history):
            return "Okay, I'll wait."
        return candidate_clean

    # If clinic clearly says the task is complete, close politely.
    if _goal_completed_from_agent(agent_text):
        if "?" not in agent_text:
            return "Thank you, that's all I needed. Goodbye."

    # If options are offered, avoid repeating or ending. Let a valid candidate through.
    if _agent_offers_options(agent_text):
        if "bye" in candidate_lower or "goodbye" in candidate_lower:
            return "That works for me. Please go ahead."
        if candidate_lower == latest or candidate_lower in latest or latest in candidate_lower:
            return "That works for me. Please go ahead."
        if _too_repetitive(candidate_clean, history):
            return "That works for me. Please go ahead."
        return candidate_clean

    # Do not end before clear completion.
    if ("bye" in candidate_lower or "goodbye" in candidate_lower) and not _goal_completed_from_agent(agent_text):
        return _continue_phrase_for_scenario(scenario)

    # Avoid mirror responses.
    if candidate_lower == latest or candidate_lower in latest or latest in candidate_lower:
        if _agent_is_processing(agent_text):
            return "Okay, I'll wait."
        if _agent_offers_options(agent_text):
            return "That works for me. Please go ahead."
        return "Okay, thank you."

    # Avoid repetition.
    if _too_repetitive(candidate_clean, history):
        if _agent_offers_options(agent_text):
            return "That works for me. Please go ahead."
        if _agent_is_processing(agent_text):
            return "Okay, I'll wait."
        return _continue_phrase_for_scenario(scenario)

    return candidate_clean


def build_prompt(scenario: Scenario, history: List[Dict[str, str]], agent_text: str) -> str:
    payload = {
        "role": "patient",
        "scenario": {
            "id": scenario.id,
            "title": scenario.title,
            "objective": scenario.objective,
        },
        "patient_profile": _as_dict(scenario.patient_profile),
        "scenario_facts_and_preferences": _as_dict(scenario.details),
        "latest_clinic_agent_text": agent_text or "[No speech captured]",
        "recent_conversation": history[-10:],
        "task": (
            "Decide the next best patient response. "
            "Classify the clinic agent's latest intent, then produce one short patient reply."
        ),
        "important": [
            "If asked for full name and date of birth together, provide both together.",
            "If asked to spell a name, spell the requested name one letter at a time.",
            "If the clinic asks whether it is speaking with the wrong patient, correct it politely.",
            "If the clinic is checking, holding, routing, or transferring, wait instead of ending.",
            "If the clinic asks what you need, state the scenario reason for the call.",
            "If the clinic says the DOB does not match but accepts it for demo purposes, continue with the reason for the call.",
            "Do not say goodbye before the task is clearly complete.",
        ],
    }
    return json.dumps(payload, indent=2)


def llm_reply(scenario: Scenario, history: List[Dict[str, str]], agent_text: str) -> str:
    settings = get_settings()

    # Identity/profile questions should override generic greetings and disclaimers.
    # Example: "Thanks for calling... Am I speaking with Maya?"
    profile_reply = _profile_field_reply(scenario, agent_text)
    if profile_reply:
        return _clean_reply(profile_reply)

    # If it is only the recording/language disclaimer, acknowledge briefly.
    # This avoids silent call failures.
    if _is_recording_disclaimer(agent_text) and not _is_real_greeting_or_help_prompt(agent_text):
        return "Okay."

    # Start the scenario after the clinic greets or asks how it can help.
    if _is_real_greeting_or_help_prompt(agent_text):
        return _clean_reply(scenario.opening)

    if settings.llm_backend != "ollama":
        raise ValueError("This no-paid-LLM version supports only LLM_BACKEND=ollama.")

    prompt = build_prompt(scenario, history, agent_text)
    raw = _ollama_reply(settings, prompt)
    parsed = _safe_json_loads(raw)

    candidate = str(parsed.get("reply", "")).strip()
    agent_intent = str(parsed.get("agent_intent", "unclear")).strip()
    goal_status = str(parsed.get("goal_status", "in_progress")).strip()

    repaired = _generic_repair(
        candidate=candidate,
        agent_intent=agent_intent,
        goal_status=goal_status,
        scenario=scenario,
        history=history,
        agent_text=agent_text,
    )

    return _clean_reply(repaired)

def _ollama_reply(settings, prompt: str) -> str:
    url = settings.ollama_url.rstrip("/") + "/api/chat"

    resp = requests.post(
        url,
        json={
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 90,
                "top_p": 0.8,
            },
        },
        timeout=settings.llm_timeout_seconds,
    )

    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")