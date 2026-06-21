from typing import Dict, List

from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from .config import get_settings
from .llm_patient import llm_reply
from .scenarios import get_scenario
from .transcripts import append_line, append_recording_info, initialize_transcript

app = FastAPI(title="Pretty Good AI Voice Bot")

# In-memory state is fine for a single local challenge run.
CALL_STATE: Dict[str, Dict[str, object]] = {}


def xml_response(vr: VoiceResponse) -> Response:
    return Response(content=str(vr), media_type="application/xml")


def add_history(history: List[Dict[str, str]], speaker: str, text: str) -> None:
    """Store both generic and speaker-keyed history.

    The LLM prompt can read speaker/text, and the repetition guard can read
    PatientBot / PrettyGoodAI keys.
    """
    history.append(
        {
            "speaker": speaker,
            "text": text,
            speaker: text,
        }
    )


def _voice_for_scenario(settings, scenario) -> str:
    """Choose patient voice from the scenario profile."""
    profile = scenario.patient_profile or {}
    gender = str(profile.get("voice_gender", "")).lower().strip()

    if gender == "male":
        return settings.male_voice_name

    if gender == "female":
        return settings.female_voice_name

    return settings.voice_name


def _gather_for_agent(settings, scenario_id: str) -> Gather:
    return Gather(
        input="speech",
        action=f"{settings.public_base_url.rstrip('/')}/voice/continue?scenario_id={scenario_id}",
        method="POST",
        speech_timeout="auto",
        timeout=8,
        language=settings.call_language,
    )


def _make_spoken_text(text: str) -> str:
    """Light cleanup so TTS sounds less robotic and more conversational."""
    text = (text or "").strip()

    replacements = {
        "I would like to": "I'd like to",
        "I am": "I'm",
        "I have been": "I've been",
        "I will": "I'll",
        "I cannot": "I can't",
        "That option works for me. Please go ahead and confirm it.": "Sure, that works for me.",
        "Can we continue scheduling the appointment?": "Could we keep going with the appointment?",
        "Can we continue with the refill request?": "Could we keep going with the refill?",
        "Can we continue with my insurance question?": "Could we keep going with my insurance question?",
        "Can we continue with the cancellation?": "Could we keep going with the cancellation?",
        "Can we continue rescheduling the appointment?": "Could we keep going with rescheduling?",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def _is_terminal_reply(reply: str) -> bool:
    low = (reply or "").lower().strip()
    return (
        "goodbye" in low
        or low.endswith("bye.")
        or low.endswith("bye")
        or "that's all i needed" in low
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.api_route("/voice/start", methods=["GET", "POST"])
async def voice_start(
    request: Request,
    CallSid: str = Form(default="UNKNOWN"),
    scenario_id: str = "appointment_simple",
):
    settings = get_settings()
    scenario = get_scenario(scenario_id)

    CALL_STATE[CallSid] = {
        "scenario_id": scenario.id,
        "bot_turn_index": 0,
        "history": [],
        "no_speech_count": 0,
    }

    initialize_transcript(
        call_sid=CallSid,
        scenario=scenario,
        from_number=settings.twilio_from_number,
        to_number=settings.target_number,
    )

    vr = VoiceResponse()

    # Let the Pretty Good AI agent greet first.
    vr.pause(length=1)

    gather = _gather_for_agent(settings, scenario.id)
    vr.append(gather)

    # If no speech is captured, continue anyway.
    vr.redirect(f"{settings.public_base_url.rstrip('/')}/voice/continue?scenario_id={scenario.id}")

    return xml_response(vr)


@app.post("/voice/continue")
async def voice_continue(
    CallSid: str = Form(default="UNKNOWN"),
    SpeechResult: str = Form(default=""),
    Confidence: str = Form(default=""),
    scenario_id: str = "appointment_simple",
):
    settings = get_settings()
    scenario = get_scenario(scenario_id)
    voice_name = _voice_for_scenario(settings, scenario)

    state = CALL_STATE.setdefault(
        CallSid,
        {
            "scenario_id": scenario.id,
            "bot_turn_index": 0,
            "history": [],
            "no_speech_count": 0,
        },
    )

    bot_turn_index = int(state.get("bot_turn_index", 0))
    history: List[Dict[str, str]] = state.setdefault("history", [])  # type: ignore[assignment]

    agent_text = SpeechResult.strip()
    vr = VoiceResponse()

    if agent_text:
        state["no_speech_count"] = 0
        confidence_text = f" (confidence={Confidence})" if Confidence else ""
        append_line(CallSid, "PrettyGoodAI", f"{agent_text}{confidence_text}")
        add_history(history, "PrettyGoodAI", agent_text)
    else:
        no_speech_count = int(state.get("no_speech_count", 0)) + 1
        state["no_speech_count"] = no_speech_count

        append_line(CallSid, "PrettyGoodAI", "[No speech captured or timeout]")
        add_history(history, "PrettyGoodAI", "[No speech captured or timeout]")

        if no_speech_count == 1:
            reply = "Sorry, I didn't catch that. Could you repeat it?"
        else:
            reply = "Could you please repeat that?"

        reply = _make_spoken_text(reply)

        append_line(CallSid, "PatientBot", reply)
        add_history(history, "PatientBot", reply)
        state["bot_turn_index"] = bot_turn_index + 1

        gather = _gather_for_agent(settings, scenario.id)
        gather.say(reply, voice=voice_name, language=settings.call_language)
        vr.append(gather)

        vr.redirect(f"{settings.public_base_url.rstrip('/')}/voice/continue?scenario_id={scenario.id}")
        return xml_response(vr)

    if bot_turn_index >= scenario.max_bot_turns:
        goodbye = _make_spoken_text("Thank you, that's all I needed. Goodbye.")

        append_line(CallSid, "PatientBot", goodbye)
        add_history(history, "PatientBot", goodbye)
        state["bot_turn_index"] = bot_turn_index + 1

        vr.say(goodbye, voice=voice_name, language=settings.call_language)
        vr.hangup()
        return xml_response(vr)

    try:
        reply = llm_reply(scenario, history, agent_text)
    except Exception as exc:
        reply = "Sorry, could you please repeat that?"
        append_line(CallSid, "System", f"LLM error: {type(exc).__name__}: {exc}")

    reply = _make_spoken_text(reply)

    append_line(CallSid, "PatientBot", reply)
    add_history(history, "PatientBot", reply)
    state["bot_turn_index"] = bot_turn_index + 1

    if _is_terminal_reply(reply):
        vr.say(reply, voice=voice_name, language=settings.call_language)
        vr.hangup()
        return xml_response(vr)

    gather = _gather_for_agent(settings, scenario.id)
    gather.say(reply, voice=voice_name, language=settings.call_language)
    vr.append(gather)

    vr.redirect(f"{settings.public_base_url.rstrip('/')}/voice/continue?scenario_id={scenario.id}")

    return xml_response(vr)


@app.post("/voice/status")
async def call_status(
    CallSid: str = Form(default="UNKNOWN"),
    CallStatus: str = Form(default=""),
    RecordingUrl: str = Form(default=""),
):
    if CallStatus:
        append_line(CallSid, "System", f"Call status: {CallStatus}")

    if RecordingUrl:
        append_recording_info(CallSid, RecordingUrl)

    return {"ok": True}