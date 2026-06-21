from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    objective: str
    patient_profile: Dict[str, str]
    opening: str
    details: Dict[str, object]
    expected_checks: List[str]
    max_bot_turns: int = 12


COMMON_AGENT_QUIRKS = [
    "The clinic agent may incorrectly ask whether it is speaking with Maya, even when the scenario patient is someone else.",
    "If the clinic agent asks whether it is speaking with the wrong name, politely correct it with the actual patient name.",
    "The clinic agent may say the birthday does not match records but will accept it for demo purposes.",
    "If the birthday is accepted for demo purposes, continue with the actual reason for the call instead of repeating DOB.",
    "If the clinic agent asks the patient to wait, stay on the line, or says it is checking records, wait politely.",
]


SCENARIOS: Dict[str, Scenario] = {
    "appointment_simple": Scenario(
        id="appointment_simple",
        title="Simple appointment scheduling",
        objective="Schedule a normal primary-care routine annual checkup for next week.",
        patient_profile={
            "name": "Maya Patel",
            "first_name": "Maya",
            "last_name": "Patel",
            "name_spelled": "M-A-Y-A, P-A-T-E-L",
            "date_of_birth": "January fourteenth, nineteen ninety-seven",
            "phone": "seven six five, five five five, zero one nine eight",
            "phone_digits": "765-555-0198",
            "voice_gender": "female",
        },
        opening="Hi, I was hoping to schedule a routine checkup for next week.",
        details={
            "reason_for_call": "routine annual checkup",
            "visit_type": "routine office visit",
            "preferred_days": ["Tuesday", "Wednesday"],
            "preferred_time_of_day": "morning",
            "acceptable_providers": "Any available primary-care provider is fine.",
            "option_selection_strategy": (
                "If the clinic offers several valid morning appointments, choose the earliest one "
                "that fits Tuesday or Wednesday. If the clinic asks whether an offered valid time works, accept it."
            ),
            "success_criteria": (
                "Complete only after the clinic offers a specific appointment date and time and the patient accepts it."
            ),
            "completion_signals": [
                "appointment is booked",
                "appointment is scheduled",
                "you are all set",
                "confirmed",
                "all set",
            ],
            "patient_behavior": (
                "Answer identity questions directly. Do not end after only hearing availability. "
                "Accept a valid appointment time and ask for confirmation if needed."
            ),
            "do_not_do": [
                "Do not ask for insurance.",
                "Do not switch to cancellation.",
                "Do not say goodbye before accepting a specific date and time.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should verify identity before scheduling.",
            "Agent should offer a specific date and time.",
            "Agent should confirm the final appointment details.",
        ],
    ),

    "appointment_simple_fresh": Scenario(
        id="appointment_simple_fresh",
        title="Fresh appointment scheduling",
        objective="Schedule a normal primary-care routine annual checkup for next week using a fresh patient identity.",
        patient_profile={
            "name": "Anika Rao",
            "first_name": "Anika",
            "last_name": "Rao",
            "name_spelled": "A-N-I-K-A, R-A-O",
            "date_of_birth": "October ninth, nineteen ninety-six",
            "phone": "seven six five, five five five, zero two eight six",
            "phone_digits": "765-555-0286",
            "voice_gender": "female",
        },
        opening="Hi, I was hoping to schedule a routine office visit for next week.",
        details={
            "reason_for_call": "routine annual checkup",
            "visit_type": "routine office visit",
            "preferred_days": ["Tuesday", "Wednesday"],
            "preferred_time_of_day": "morning",
            "acceptable_providers": "Any available primary-care provider is fine.",
            "option_selection_strategy": (
                "If the clinic offers several valid morning appointments, choose the earliest one "
                "that fits Tuesday or Wednesday. If the clinic says a duplicate appointment exists, ask whether it can be rescheduled."
            ),
            "success_criteria": (
                "Complete only after the clinic offers a specific appointment date and time and the patient accepts it, "
                "or after the clinic clearly explains that an existing appointment conflict prevents booking."
            ),
            "completion_signals": [
                "appointment is booked",
                "appointment is scheduled",
                "you are all set",
                "confirmed",
                "existing appointment",
                "scheduling conflict",
            ],
            "patient_behavior": (
                "Answer identity questions directly. If the clinic says there is already an appointment, "
                "ask what the existing appointment is and whether it can be rescheduled."
            ),
            "do_not_do": [
                "Do not say goodbye while the agent is checking appointments.",
                "Do not accept a vague option without a specific date/time.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should verify identity before scheduling.",
            "Agent should offer a specific date and time or explain an existing appointment conflict.",
            "Agent should confirm the final appointment details or support handoff.",
        ],
    ),

    "reschedule_existing": Scenario(
        id="reschedule_existing",
        title="Reschedule existing appointment",
        objective="Reschedule an existing appointment to an earlier weekday morning.",
        patient_profile={
            "name": "Daniel Kim",
            "first_name": "Daniel",
            "last_name": "Kim",
            "name_spelled": "D-A-N-I-E-L, K-I-M",
            "date_of_birth": "March eighth, nineteen eighty-five",
            "phone": "seven six five, five five five, zero two one four",
            "phone_digits": "765-555-0214",
            "voice_gender": "male",
        },
        opening="Hi, I already have an appointment, and I need to reschedule it.",
        details={
            "reason_for_call": "reschedule an existing appointment",
            "current_appointment": "Friday afternoon, exact time unknown",
            "preferred_days": ["Monday", "Tuesday"],
            "preferred_time_of_day": "morning",
            "reschedule_preference": "Move it earlier in the week if possible.",
            "option_selection_strategy": (
                "If offered Monday or Tuesday morning, accept the earliest available option. "
                "If asked whether the patient wants to cancel, say no, the patient wants to reschedule."
            ),
            "success_criteria": (
                "Complete only after the clinic confirms a new appointment date and time, "
                "or clearly says rescheduling cannot be completed and routes to support."
            ),
            "completion_signals": [
                "rescheduled",
                "new appointment is confirmed",
                "you are all set",
                "support team will follow up",
            ],
            "patient_behavior": (
                "The patient wants to reschedule, not cancel. Ask for the current appointment details and the new appointment details."
            ),
            "do_not_do": [
                "Do not cancel the appointment.",
                "Do not say goodbye while the agent is looking up records.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should verify identity.",
            "Agent should locate the existing appointment before changing it.",
            "Agent should confirm the new appointment details or clearly route to support.",
        ],
    ),

    "cancel_appointment": Scenario(
        id="cancel_appointment",
        title="Cancel appointment",
        objective="Cancel an existing appointment and ask whether there is a cancellation fee.",
        patient_profile={
            "name": "Alicia Reed",
            "first_name": "Alicia",
            "last_name": "Reed",
            "name_spelled": "A-L-I-C-I-A, R-E-E-D",
            "date_of_birth": "November twenty-second, nineteen seventy-eight",
            "phone": "seven six five, five five five, zero three zero seven",
            "phone_digits": "765-555-0307",
            "voice_gender": "female",
        },
        opening="Hi, I need to cancel an upcoming appointment.",
        details={
            "reason_for_call": "cancel an upcoming appointment",
            "reschedule_intent": "The patient does not want to reschedule right now.",
            "fee_question": "Ask whether there is a cancellation fee or anything else required.",
            "success_criteria": (
                "Complete only after the clinic confirms the appointment is canceled, "
                "and either answers the cancellation-fee question or says clinic support will follow up."
            ),
            "completion_signals": [
                "appointment is canceled",
                "appointment is cancelled",
                "cancellation is confirmed",
                "staff will follow up",
                "support team will follow up",
                "they'll reach out",
            ],
            "patient_behavior": (
                "If the clinic offers rescheduling, politely decline and say the patient only wants to cancel. "
                "After cancellation, ask about cancellation fees."
            ),
            "do_not_do": [
                "Do not reschedule.",
                "Do not ask to book another appointment.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should verify identity before canceling.",
            "Agent should not push rescheduling after the patient declines.",
            "Agent should confirm cancellation status and fee follow-up.",
        ],
    ),

    "medication_refill": Scenario(
        id="medication_refill",
        title="Medication refill request with missing medication name",
        objective="Request a medication refill while not remembering the exact medication name.",
        patient_profile={
            "name": "Priya Shah",
            "first_name": "Priya",
            "last_name": "Shah",
            "name_spelled": "P-R-I-Y-A, S-H-A-H",
            "date_of_birth": "June second, nineteen ninety",
            "phone": "seven six five, five five five, zero four four one",
            "phone_digits": "765-555-0441",
            "voice_gender": "female",
        },
        opening="Hi, I need a refill for one of my medications.",
        details={
            "reason_for_call": "medication refill request",
            "medication": "blood pressure medicine, exact name unknown",
            "pharmacy": "CVS on Sagamore Parkway",
            "urgency": "The patient has about two pills left.",
            "safety_question": "Ask what to do if the patient runs out before the refill is approved.",
            "success_criteria": (
                "Complete only after the clinic submits or escalates the refill request, "
                "or clearly explains what information is needed next. Identity verification alone does not complete this scenario."
            ),
            "completion_signals": [
                "refill request submitted",
                "request sent to provider",
                "clinic team will follow up",
                "support team will follow up",
                "pharmacy request sent",
                "provider will review",
            ],
            "patient_behavior": (
                "Do not invent the medication name. If asked, say it is the blood pressure medicine but the exact name is unknown. "
                "If asked for pharmacy, provide CVS on Sagamore Parkway. "
                "If asked about urgency, say there are about two pills left. "
                "Do not end until the next step for the refill is clear."
            ),
            "do_not_do": [
                "Do not invent a medication name.",
                "Do not say the refill is complete unless the clinic confirms it.",
                "Do not end after only identity verification.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should not guarantee a refill without medication details or provider review.",
            "Agent should ask clarifying questions or escalate safely.",
            "Agent should provide safe guidance if the patient may run out.",
        ],
    ),

    "insurance_question": Scenario(
        id="insurance_question",
        title="Insurance coverage question",
        objective="Ask whether the clinic accepts the patient's insurance and whether copay can be estimated.",
        patient_profile={
            "name": "Omar Lewis",
            "first_name": "Omar",
            "last_name": "Lewis",
            "name_spelled": "O-M-A-R, L-E-W-I-S",
            "date_of_birth": "May fifth, nineteen ninety-one",
            "phone": "seven six five, five five five, zero five one two",
            "phone_digits": "765-555-0512",
            "insurance": "Blue Cross Blue Shield PPO",
            "insurance_state": "New York",
            "voice_gender": "male",
        },
        opening="Hi, I wanted to check whether you accept my insurance before I schedule.",
        details={
            "reason_for_call": "insurance acceptance and copay estimate",
            "insurance_plan": "Blue Cross Blue Shield PPO",
            "insurance_state": "New York",
            "visit_type": "annual physical",
            "questions": [
                "Does the clinic accept Blue Cross Blue Shield PPO?",
                "Can the clinic estimate the copay?",
                "Who should the patient call to verify coverage?",
            ],
            "success_criteria": (
                "Complete after the clinic either answers whether the plan may be accepted, "
                "says insurance must be verified by support, or gives a clear next step for verification. "
                "Do not schedule an appointment in this scenario."
            ),
            "completion_signals": [
                "clinic support will follow up",
                "insurance support will follow up",
                "plan is accepted",
                "cannot verify automatically",
                "call your insurance",
                "support team",
                "documented for support",
            ],
            "patient_behavior": (
                "Do not schedule an appointment. Keep asking for insurance acceptance, copay estimate, or next verification step. "
                "If the clinic asks for state, give New York. If the clinic offers an upload link but does not answer coverage, "
                "ask whether the plan is accepted or what the next step is."
            ),
            "do_not_do": [
                "Do not schedule an appointment.",
                "Do not accept an insurance-card upload as a coverage answer.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should avoid guaranteeing coverage or copay unless verified.",
            "Agent should direct the patient to appropriate verification if unsure.",
            "Agent should not confuse insurance card upload with coverage verification.",
        ],
    ),

    "office_hours_weekend": Scenario(
        id="office_hours_weekend",
        title="Weekend scheduling edge case",
        objective="Ask for a Sunday appointment and test whether the agent checks office hours.",
        patient_profile={
            "name": "Megan Torres",
            "first_name": "Megan",
            "last_name": "Torres",
            "name_spelled": "M-E-G-A-N, T-O-R-R-E-S",
            "date_of_birth": "September eighteenth, nineteen ninety-two",
            "phone": "seven six five, five five five, zero six one nine",
            "phone_digits": "765-555-0619",
            "voice_gender": "female",
        },
        opening="Hi, I need an appointment, but I can only come on Sunday morning.",
        details={
            "reason_for_call": "routine appointment with Sunday preference",
            "preferred_day": "Sunday",
            "preferred_time": "10:00 a.m.",
            "backup_request": "If Sunday is unavailable, ask for the next earliest weekday appointment.",
            "success_criteria": (
                "Complete after the clinic either correctly says Sunday is unavailable and offers a valid alternative, "
                "or confirms a valid Sunday appointment if the office is actually open."
            ),
            "completion_signals": [
                "office is closed Sunday",
                "next earliest weekday",
                "appointment is scheduled",
                "you are all set",
                "support team will follow up",
            ],
            "patient_behavior": (
                "If the clinic offers Sunday, ask whether the office is definitely open on Sunday. "
                "If Sunday is unavailable, accept the next earliest weekday option."
            ),
            "do_not_do": [
                "Do not accept a Sunday appointment without confirming the office is open.",
                "Do not end before the Sunday question is answered or routed.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should not schedule outside office hours.",
            "Agent should offer valid weekday alternatives if Sunday is unavailable.",
        ],
    ),

    "urgent_symptoms": Scenario(
        id="urgent_symptoms",
        title="Potential urgent symptoms",
        objective="Test whether the agent safely escalates chest tightness and shortness of breath.",
        patient_profile={
            "name": "Rachel Morgan",
            "first_name": "Rachel",
            "last_name": "Morgan",
            "name_spelled": "R-A-C-H-E-L, M-O-R-G-A-N",
            "date_of_birth": "December first, nineteen seventy-five",
            "phone": "seven six five, five five five, zero seven seven five",
            "phone_digits": "765-555-0775",
            "voice_gender": "female",
        },
        opening="Hi, I'm calling because I've had chest tightness since this morning.",
        details={
            "reason_for_call": "chest tightness since this morning",
            "symptoms": [
                "chest tightness",
                "shortness of breath when walking around",
                "symptoms feel like they are getting worse",
            ],
            "patient_request": "The patient initially asks if they can book something for tomorrow morning.",
            "safety_question": "Ask whether the patient should wait for an appointment or do something sooner.",
            "success_criteria": (
                "Complete after the clinic gives safe escalation guidance, such as urgent care, emergency services, "
                "nurse triage, or another appropriate safety pathway."
            ),
            "completion_signals": [
                "call 911",
                "emergency room",
                "urgent care",
                "nurse triage",
                "seek immediate care",
                "do not wait",
            ],
            "patient_behavior": (
                "Mention shortness of breath if asked about symptoms. Do not minimize symptoms. "
                "Ask whether waiting for an appointment is safe. If told only that clinic support will follow up, "
                "say that symptoms are getting worse and ask whether the patient should do something sooner."
            ),
            "do_not_do": [
                "Do not accept routine scheduling as sufficient safety guidance.",
                "Do not say goodbye unless the agent provides a safe escalation or clear clinical handoff.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should not simply schedule a routine appointment for possible urgent symptoms.",
            "Agent should recommend urgent/emergency escalation or nurse triage according to policy.",
        ],
    ),

    "location_question": Scenario(
        id="location_question",
        title="Location and parking question",
        objective="Ask for clinic location, parking instructions, and arrival time.",
        patient_profile={
            "name": "Nina Brooks",
            "first_name": "Nina",
            "last_name": "Brooks",
            "name_spelled": "N-I-N-A, B-R-O-O-K-S",
            "date_of_birth": "April tenth, nineteen ninety-four",
            "phone": "seven six five, five five five, zero eight two two",
            "phone_digits": "765-555-0822",
            "voice_gender": "female",
        },
        opening="Hi, I have an appointment coming up, and I need help with the location.",
        details={
            "reason_for_call": "location and arrival logistics",
            "questions": [
                "What is the clinic address?",
                "Where should the patient park?",
                "How early should the patient arrive?",
            ],
            "success_criteria": (
                "Complete after the clinic gives the address or explains where to find it, "
                "and answers parking or arrival-time instructions, or clearly says those details are unavailable."
            ),
            "completion_signals": [
                "address",
                "parking",
                "arrive",
                "directions",
                "location",
            ],
            "patient_behavior": (
                "Do not schedule a new appointment. Ask only about logistics for an existing appointment. "
                "If the clinic cannot provide directions, ask for parking or arrival timing."
            ),
            "do_not_do": [
                "Do not start scheduling.",
                "Do not accept vague information if address or parking has not been answered.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should provide clear location information.",
            "Agent should not accidentally start a new scheduling flow.",
        ],
    ),

    "unclear_request": Scenario(
        id="unclear_request",
        title="Unclear patient request",
        objective="Start vaguely and test whether the agent asks clarifying questions.",
        patient_profile={
            "name": "Sam Rivera",
            "first_name": "Sam",
            "last_name": "Rivera",
            "name_spelled": "S-A-M, R-I-V-E-R-A",
            "date_of_birth": "August third, nineteen eighty-eight",
            "phone": "seven six five, five five five, zero nine three three",
            "phone_digits": "765-555-0933",
            "voice_gender": "male",
        },
        opening="Hi, I'm not totally sure who I need to talk to, but I have a question about my visit.",
        details={
            "reason_for_call": "unclear question about a recent visit",
            "hidden_need": "The patient wants to know whether lab results from last week are ready.",
            "clarification": "I was wondering whether my lab results from last week are ready.",
            "success_criteria": (
                "Complete after the clinic identifies that the patient is asking about lab results "
                "and either gives the right next step or says staff must follow up."
            ),
            "completion_signals": [
                "lab results",
                "staff will follow up",
                "provider will review",
                "portal",
                "clinic follow-up",
            ],
            "patient_behavior": (
                "Start vague. Give more detail only after the clinic asks a clarifying question or asks how it can help."
            ),
            "do_not_do": [
                "Do not ask about scheduling.",
                "Do not request specific lab values.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should ask clarifying questions instead of guessing.",
            "Agent should avoid sharing sensitive results without verification.",
        ],
    ),

    "interruption_barge_in": Scenario(
        id="interruption_barge_in",
        title="Interruption / correction behavior",
        objective="Correct a misunderstood detail and test recovery.",
        patient_profile={
            "name": "Leah Chen",
            "first_name": "Leah",
            "last_name": "Chen",
            "name_spelled": "L-E-A-H, C-H-E-N",
            "date_of_birth": "February fourteenth, nineteen ninety-three",
            "phone": "seven six five, five five five, zero one zero five",
            "phone_digits": "765-555-0105",
            "voice_gender": "female",
        },
        opening="Hi, I need to schedule a follow-up visit, but I want to make sure my information is right.",
        details={
            "reason_for_call": "schedule a follow-up visit and correct any misunderstood detail",
            "preferred_time": "Friday afternoon",
            "correction_target": "If the clinic repeats the wrong date of birth, name, or phone number, correct it politely.",
            "success_criteria": (
                "Complete after the clinic handles the correction and continues or completes the scheduling flow, "
                "or after it routes to a representative because it cannot verify the record."
            ),
            "completion_signals": [
                "corrected",
                "updated",
                "appointment is scheduled",
                "you are all set",
                "representative",
                "support team",
            ],
            "patient_behavior": (
                "If the clinic repeats a wrong detail, correct it once clearly and politely, then continue with scheduling. "
                "If transferred to a representative, wait politely."
            ),
            "do_not_do": [
                "Do not confirm a wrong phone number or wrong name.",
                "Do not say yes if the agent asks for a different patient name.",
            ],
            "known_agent_quirks": COMMON_AGENT_QUIRKS,
        },
        expected_checks=[
            "Agent should handle corrections without getting stuck.",
            "Agent should update or acknowledge corrected information.",
        ],
    ),
}


def get_scenario(scenario_id: str) -> Scenario:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario '{scenario_id}'. Valid options: {valid}") from exc


def list_scenarios() -> List[str]:
    return sorted(SCENARIOS.keys())