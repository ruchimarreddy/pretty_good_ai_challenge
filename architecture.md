# Architecture

The goal of this project was to build a realistic patient caller for the Pretty Good AI assessment line. I wanted the bot to actually call the clinic agent, listen to what it says, respond like a patient, and save enough evidence to understand where the agent works well and where it struggles.

At a high level, the setup is simple. Twilio places the outbound call and handles the phone audio. The call connects to my local FastAPI server through ngrok. When Pretty Good AI speaks, Twilio sends the recognized speech to my server. The server logs that turn, asks PatientBot what the patient should say next, and returns TwiML so Twilio can speak the response back into the call.

I kept the architecture intentionally small. Twilio handles the real phone call, recording, and speech capture. Python handles the scenario state, transcript logging, and patient response logic. For the patient-agent brain, I used a local Ollama model instead of a paid LLM API. This kept the project reproducible and low-cost. The tradeoff is that a local model can be slower or less consistent than a hosted model, so I kept the prompts short, made the spoken replies short, and added guardrails for common clinic questions like name, date of birth, phone number, insurance, and confirmations.

## High-Level Flow

```text
call_runner.py
    ↓
Twilio outbound call
    ↓
Pretty Good AI assessment number
    ↓
FastAPI webhook exposed through ngrok
    ↓
Twilio speech recognition captures Pretty Good AI response
    ↓
PatientBot generates the next patient response
    ↓
FastAPI returns TwiML with <Say> + <Gather>
    ↓
Transcript and recording are saved
```

## Core Components

### 1. `call_runner.py`

`call_runner.py` starts the outbound Twilio call. It chooses which scenario to run and sends Twilio to the local webhook endpoint:

```text
/voice/start?scenario_id=<scenario_id>
```

For example:

```bash
python -m pgai_bot.call_runner --scenario insurance_question
```

It can also run all scenarios:

```bash
python -m pgai_bot.call_runner --all
```

### 2. `server.py`

`server.py` is the FastAPI webhook that controls the call loop.

It has four main jobs:

* start the call and let Pretty Good AI speak first,
* receive Twilio speech results from Pretty Good AI,
* log each Pretty Good AI and PatientBot turn into the transcript,
* ask `llm_patient.py` for the next patient response and speak it back using Twilio.

The main endpoints are:

```text
GET/POST /voice/start
POST     /voice/continue
POST     /voice/status
GET      /health
```

For this challenge, I kept call state in a simple in-memory `CALL_STATE` dictionary. Since I was running one local test setup at a time, that was enough. In production, I would move this to Redis or a database.

### 3. `scenarios.py`

`scenarios.py` contains the synthetic patient scenarios. I kept the patient facts here so the response logic does not become a hardcoded script for each call.

Each scenario includes things like:

* patient name,
* date of birth,
* phone number,
* reason for calling,
* patient preferences,
* expected behavior from the clinic agent,
* max number of turns,
* and optional voice gender.

The final scenario set covers appointment scheduling, cancellation, insurance questions, refill requests, urgent symptoms, weekend scheduling, location questions, unclear lab-result questions, and correction behavior.

### 4. `llm_patient.py`

`llm_patient.py` is the PatientBot brain. It combines a local LLM with deterministic handling for the parts of the call that need to be reliable.

I did not want the LLM to freely invent patient information, so common identity questions are handled directly in code. For example, if the clinic asks for DOB, phone number, last name, or insurance plan, PatientBot answers from the scenario profile.

The deterministic layer handles:

* name and full-name questions,
* date of birth questions,
* phone number questions,
* insurance plan questions,
* spelling requests,
* confirmation questions,
* wrong-name correction,
* handoff/waiting behavior,
* repeated answers,
* and premature goodbye prevention.

For more open-ended turns, the local Ollama model gets the scenario objective, patient profile, scenario facts, latest Pretty Good AI text, and recent conversation history. It then returns one short patient reply.

The goal was not to make a perfect medical assistant. The goal was to make a realistic patient simulator that stays grounded in the scenario and creates useful test evidence.

### 5. `transcripts.py`

`transcripts.py` handles transcript creation and logging. Each call gets a transcript with:

* scenario ID and title,
* objective,
* patient profile,
* expected checks,
* Pretty Good AI turns,
* PatientBot turns,
* call status,
* and recording metadata if available.

The final bug report is based on these transcripts and matching audio recordings.

### 6. `config.py`

`config.py` loads settings from `.env` using Pydantic settings. This keeps secrets and local runtime values out of the code.

Important settings include:

```env
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
TARGET_NUMBER
PUBLIC_BASE_URL
CALL_LANGUAGE
VOICE_NAME
FEMALE_VOICE_NAME
MALE_VOICE_NAME
LLM_BACKEND
OLLAMA_URL
OLLAMA_MODEL
LLM_TIMEOUT_SECONDS
```

The real `.env` file is ignored by Git. `.env.example` shows what variables are needed without exposing secrets.

## Voice Design

I added simple scenario-based voice selection so male and female patient profiles do not all sound the same.

Example:

```env
FEMALE_VOICE_NAME=Polly.Joanna
MALE_VOICE_NAME=Polly.Matthew
```

This is a small detail, but it made the calls feel more natural during testing.

## Prompting Strategy

The LLM is not asked to manage the whole phone call by itself. That was too unpredictable for identity-heavy clinic flows.

Instead, the prompt gives the model:

* the patient role,
* the scenario objective,
* the patient profile,
* the scenario facts and preferences,
* the latest Pretty Good AI text,
* recent conversation history,
* and rules about staying in character and not inventing details.

The model only needs to produce the next short patient sentence. After that, the reply is cleaned and checked by the guardrail layer before it is spoken.

## Guardrail Strategy

I added guardrails because real voice calls have a lot of repetitive and messy moments. Pretty Good AI sometimes asked for the same identity details several times, repeated partial phone numbers, or routed to support. The patient bot needed to handle those without sounding completely lost.

The most important guardrails are:

* correct the agent if it asks for the wrong patient name,
* repeat exact DOB and phone values when asked,
* avoid inventing medication names, insurance details, dates, or appointment times,
* avoid saying goodbye before the scenario is actually complete,
* wait during handoff or transfer instead of asking unrelated questions,
* close naturally when the agent clearly finishes,
* and avoid repeating the same patient sentence too many times.

These guardrails improved the quality of the final calls and made the transcripts more useful for evaluating Pretty Good AI instead of just evaluating my patient bot.

## Transcript and Recording Output

The final selected evidence is stored in:

```text
transcripts/
recordings/
```

Each selected call has a matching transcript and recording. For example:

```text
transcripts/call_04_urgent_symptoms.txt
recordings/call_04_urgent_symptoms.mp3
```

The bug report references these files directly.

## Design Tradeoffs

### Local LLM vs hosted LLM

I used Ollama to avoid paid LLM APIs and keep the project easy to reproduce locally. The tradeoff is that local models can be slower and sometimes less polished than hosted models.

### Deterministic logic vs fully agentic behavior

A fully LLM-driven patient bot was too unpredictable for clinic calls. Identity details like name, DOB, phone number, and insurance should be exact, so I handled those with deterministic logic and used the LLM only where flexibility was useful.

### Simple in-memory state vs persistent storage

For this challenge, one local run at a time was enough. A simple in-memory state dictionary kept the code easy to understand. For production, I would use Redis or a database.

### Real phone calls vs text-only simulation

I used real calls because the challenge is about voice interaction quality. Real calls expose latency, awkward pauses, speech recognition errors, interruptions, and handoff problems that text-only simulations would miss.

## Limitations

* Twilio speech recognition can mis-transcribe partial or noisy Pretty Good AI utterances.
* The local LLM can still produce imperfect patient responses.
* The system is for evaluation only, not real patient communication.
* No real patient information is used.
* PatientBot does not provide medical advice.
* Call state is local and in-memory.
* The system depends on ngrok and the local server staying online during calls.

## Future Improvements

If I had more time, I would add:

* automatic scoring for each scenario’s expected checks,
* unit tests for `llm_patient.py` guardrails,
* replay mode to test from saved transcripts without making new calls,
* structured call summaries after each run,
* automatic severity tagging for bugs,
* automatic redaction for Twilio URLs or identifiers,
* latency tracking for each response turn,
* and better scenario-completion detection.
