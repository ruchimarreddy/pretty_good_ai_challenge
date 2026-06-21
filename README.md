# Pretty Good AI Voice Bot Challenge

This is my submission for the Pretty Good AI AI Engineering Challenge. I built a voice-based patient simulator that calls the Pretty Good AI assessment number, talks to the clinic agent like a realistic patient, saves transcripts/recordings, and helps identify where the agent works well or breaks down.

## Overview

The main bot in this project is `PatientBot`. It acts like a synthetic patient during a real phone call.

PatientBot can:

* place outbound calls using Twilio,
* listen to Pretty Good AI through Twilio speech recognition,
* respond as a patient using a local Ollama model,
* handle common identity questions like name, DOB, phone number, and insurance,
* save transcripts and recordings for review,
* and test realistic healthcare scenarios like scheduling, cancellation, insurance, refills, urgent symptoms, and location questions.

I used a local Ollama model instead of a paid LLM API. This kept the project cheaper and easier to run locally. Twilio call charges may still apply because the testing uses real phone calls.

## Stack

* Twilio Programmable Voice for outbound calls and recordings
* FastAPI for the webhook server
* TwiML for call control
* ngrok to expose the local server
* Ollama for the local patient-agent brain
* A local Llama model, such as `llama3.2:3b`
* Amazon Polly voices through Twilio for patient speech

## Project Structure

```text
.
├── README.md
├── architecture.md
├── bug_report.md
├── .env.example
├── requirements.txt
├── pyproject.toml
├── src/
│   └── pgai_bot/
│       ├── call_runner.py
│       ├── config.py
│       ├── llm_patient.py
│       ├── scenarios.py
│       ├── server.py
│       └── transcripts.py
├── recordings/
│   ├── call_01_location_updated.mp3
│   ├── call_02_insurance_updated.mp3
│   ├── call_03_location_smooth.mp3
│   ├── call_04_urgent_symptoms.mp3
│   ├── call_05_cancel_appointment.mp3
│   ├── call_06_unclear_lab_results.mp3
│   ├── call_07_weekend_hours.mp3
│   ├── call_08_insurance_system_issue.mp3
│   ├── call_09_medication_refill.mp3
│   └── call_10_successful_appointment.mp3
└── transcripts/
    ├── call_01_location_updated.txt
    ├── call_02_insurance_updated.txt
    ├── call_03_location_smooth.txt
    ├── call_04_urgent_symptoms.txt
    ├── call_05_cancel_appointment.txt
    ├── call_06_unclear_lab_results.txt
    ├── call_07_weekend_hours.txt
    ├── call_08_insurance_system_issue.txt
    ├── call_09_medication_refill.txt
    └── call_10_successful_appointment.txt
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

Install and run Ollama:

```bash
brew install ollama
ollama serve
```

In another terminal, pull a small local model:

```bash
ollama pull llama3.2:3b
```

You can check available models with:

```bash
ollama list
```

## Environment Variables

Create a local `.env` file:

```bash
cp .env.example .env
```

Fill `.env` with your Twilio values, Pretty Good AI assessment number, ngrok URL, and Ollama settings:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
TARGET_NUMBER=+18054398008
PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app

CALL_LANGUAGE=en-US
VOICE_NAME=Polly.Joanna
FEMALE_VOICE_NAME=Polly.Joanna
MALE_VOICE_NAME=Polly.Matthew

LLM_BACKEND=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
LLM_TIMEOUT_SECONDS=18
```

Do not commit the real `.env` file. It is ignored by Git.

## Running Locally

Terminal 1: start the FastAPI webhook server.

```bash
source .venv/bin/activate
uvicorn pgai_bot.server:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2: start ngrok.

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL from ngrok into `PUBLIC_BASE_URL` in `.env`.

Check that the server is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

I also used this curl test before making real calls, just to make sure the Twilio webhook was returning TwiML correctly:

```bash
curl -X POST "http://localhost:8000/voice/continue?scenario_id=location_question" \
  -d "CallSid=TEST123" \
  -d "SpeechResult=Be recorded for quality and training purposes." \
  -d "Confidence=0.95"
```

The response should include TwiML with a `<Say>` response.

## Running a Scenario

Start one test call:

```bash
python -m pgai_bot.call_runner --scenario appointment_simple
```

Other available scenarios:

```bash
python -m pgai_bot.call_runner --scenario appointment_simple_fresh
python -m pgai_bot.call_runner --scenario reschedule_existing
python -m pgai_bot.call_runner --scenario cancel_appointment
python -m pgai_bot.call_runner --scenario medication_refill
python -m pgai_bot.call_runner --scenario insurance_question
python -m pgai_bot.call_runner --scenario office_hours_weekend
python -m pgai_bot.call_runner --scenario urgent_symptoms
python -m pgai_bot.call_runner --scenario location_question
python -m pgai_bot.call_runner --scenario unclear_request
python -m pgai_bot.call_runner --scenario interruption_barge_in
```

Run all scenarios:

```bash
python -m pgai_bot.call_runner --all
```

I recommend testing one or two calls first before running a larger batch, because these are real phone calls and Twilio charges may apply.

## Final Selected Calls

I selected 10 calls for the final evidence set. Each one has a transcript and a matching recording.

| # | Scenario | Transcript | Recording |
|---|---|---|---|
| 1 | Location / updated bot behavior | `transcripts/call_01_location_updated.txt` | `recordings/call_01_location_updated.mp3` |
| 2 | Insurance / updated bot behavior | `transcripts/call_02_insurance_updated.txt` | `recordings/call_02_insurance_updated.mp3` |
| 3 | Location / smoother address flow | `transcripts/call_03_location_smooth.txt` | `recordings/call_03_location_smooth.mp3` |
| 4 | Urgent symptoms | `transcripts/call_04_urgent_symptoms.txt` | `recordings/call_04_urgent_symptoms.mp3` |
| 5 | Cancel appointment | `transcripts/call_05_cancel_appointment.txt` | `recordings/call_05_cancel_appointment.mp3` |
| 6 | Unclear lab-results request | `transcripts/call_06_unclear_lab_results.txt` | `recordings/call_06_unclear_lab_results.mp3` |
| 7 | Weekend office-hours request | `transcripts/call_07_weekend_hours.txt` | `recordings/call_07_weekend_hours.mp3` |
| 8 | Insurance system issue | `transcripts/call_08_insurance_system_issue.txt` | `recordings/call_08_insurance_system_issue.mp3` |
| 9 | Medication refill | `transcripts/call_09_medication_refill.txt` | `recordings/call_09_medication_refill.mp3` |
| 10 | Successful appointment booking | `transcripts/call_10_successful_appointment.txt` | `recordings/call_10_successful_appointment.mp3` |



## Outputs

* `transcripts/` contains the final call transcripts.
* `recordings/` contains the matching downloaded call recordings.
* `bug_report.md` summarizes the main issues I found.
* `architecture.md` explains how the system works and the tradeoffs I made.

## Notes on Iteration

The first version of PatientBot was not perfect. During testing, I noticed a few issues in my own bot:

* It sometimes said “Yes” when Pretty Good AI asked for the wrong patient name.
* It repeated DOB after the agent said the mismatch was accepted for demo purposes.
* It sometimes ended too early during handoff.
* It used one voice for every patient.
* It sometimes gave incomplete responses to spelling or confirmation prompts.

I updated the bot to handle these better:

* wrong-name correction, such as “No, this is Omar Lewis,”
* scenario-based male/female voice selection,
* more reliable identity and confirmation handling,
* better waiting behavior during handoff,
* more structured scenario metadata,
* and cleaner transcript formatting.

Some final transcripts still include earlier behavior because those calls were useful for finding real call-flow and product issues.

## Safety Note

This project is only for challenge evaluation. All patient profiles are synthetic. PatientBot does not provide medical advice and should not be used for real patient communication or real clinical triage.

## Cost Note

The LLM runs locally through Ollama, so no paid LLM API is required. Twilio call charges may still apply because the project uses real phone calls and recordings.
