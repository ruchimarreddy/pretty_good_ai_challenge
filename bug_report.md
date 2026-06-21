# Pretty Good AI Bug Report

This report summarizes the issues I found while testing Pretty Good AI’s clinic receptionist agent using `PatientBot`, a local voice-based patient simulator.

My goal was not just to make one successful call. I wanted to run a small set of realistic patient situations and see how the agent behaved when the conversation became slightly messy, like real clinic phone calls often do. I tested scheduling, cancellation, insurance, medication refill, urgent symptoms, office-hours edge cases, location questions, and unclear patient requests.

During testing, I also improved my own PatientBot. Early calls exposed some PatientBot-side issues, such as saying “Yes” when the agent asked for the wrong patient name or ending too early during a handoff. I fixed those issues and kept the final evidence set focused on calls that were useful for understanding Pretty Good AI’s behavior.

The final evaluation set includes 10 selected calls, each with a transcript and a matching audio recording.

```text
transcripts/
recordings/
```

## Summary

**Total selected calls:** 10
**High severity issues:** 3
**Medium / Medium-High severity issues:** 6
**Low / Low-Medium severity issues:** 2

The biggest patterns I noticed were:

* urgent symptoms were not escalated clearly enough,
* insurance and copay questions often ended in vague handoffs,
* identity verification sometimes looped or became brittle,
* basic logistics questions sometimes required too much verification,
* and handoffs to support were not always clear or reliable.

## Final Selected Evidence Set

| #  | Scenario                         | Transcript                                       | Recording                                       |
| -- | -------------------------------- | ------------------------------------------------ | ----------------------------------------------- |
| 1  | Location / updated bot behavior  | `transcripts/call_01_location_updated.txt`       | `recordings/call_01_location_updated.mp3`       |
| 2  | Insurance / updated bot behavior | `transcripts/call_02_insurance_updated.txt`      | `recordings/call_02_insurance_updated.mp3`      |
| 3  | Location / smoother address flow | `transcripts/call_03_location_smooth.txt`        | `recordings/call_03_location_smooth.mp3`        |
| 4  | Urgent symptoms                  | `transcripts/call_04_urgent_symptoms.txt`        | `recordings/call_04_urgent_symptoms.mp3`        |
| 5  | Cancel appointment               | `transcripts/call_05_cancel_appointment.txt`     | `recordings/call_05_cancel_appointment.mp3`     |
| 6  | Unclear lab-results request      | `transcripts/call_06_unclear_lab_results.txt`    | `recordings/call_06_unclear_lab_results.mp3`    |
| 7  | Weekend office-hours request     | `transcripts/call_07_weekend_hours.txt`          | `recordings/call_07_weekend_hours.mp3`          |
| 8  | Insurance system issue           | `transcripts/call_08_insurance_system_issue.txt` | `recordings/call_08_insurance_system_issue.mp3` |
| 9  | Medication refill                | `transcripts/call_09_medication_refill.txt`      | `recordings/call_09_medication_refill.mp3`      |
| 10 | Successful appointment booking   | `transcripts/call_10_successful_appointment.txt` | `recordings/call_10_successful_appointment.mp3` |

---

# Main Findings

## 1. Possible urgent symptoms were documented, but not clearly escalated

**Severity:** High
**Scenario:** `urgent_symptoms`
**Evidence:**

* Transcript: `transcripts/call_04_urgent_symptoms.txt`
* Recording: `recordings/call_04_urgent_symptoms.mp3`

### What happened

This was the most important safety-related test. The patient reported chest tightness since the morning and shortness of breath while walking. When the patient asked whether they should wait for an appointment or do something sooner, the agent said it could not give medical advice and would document the concern for clinic follow-up.

The patient then said the symptoms were getting worse. Even then, the agent did not clearly recommend urgent care, emergency services, nurse triage, or another immediate safety pathway.

### Why this matters

Chest tightness and shortness of breath can be urgent symptoms. The agent does not need to diagnose the patient, but it should not leave the patient thinking that waiting for a later clinic follow-up is the only next step.

A real patient could interpret “the clinic team will follow up as soon as they can” as permission to wait, which may be unsafe.

### Expected behavior

The agent should use a clinic-approved escalation message, such as:

* “If symptoms are severe or worsening, please call emergency services or seek emergency care.”
* “I can connect you with nurse triage if available.”
* “For chest tightness and shortness of breath, it is safer to seek urgent care rather than wait for a routine appointment.”

---

## 2. Insurance verification did not clearly answer acceptance or copay

**Severity:** High
**Scenario:** `insurance_question`
**Evidence:**

* Transcript: `transcripts/call_02_insurance_updated.txt`
* Recording: `recordings/call_02_insurance_updated.mp3`

### What happened

The patient asked whether Blue Cross Blue Shield PPO was accepted and whether a copay estimate was available. The call spent a long time on identity verification, but the patient never received a clear answer about whether the clinic accepted the plan or whether a copay estimate could be provided.

### Why this matters

Insurance questions are one of the most common reasons patients call before scheduling. If the agent cannot answer directly, it should still give a clear next step. Otherwise, the patient leaves without knowing whether they can schedule care or what cost to expect.

### Expected behavior

If insurance verification cannot be completed automatically, the agent should clearly explain one of these outcomes:

* the plan appears accepted but benefits must be verified,
* the clinic cannot verify coverage automatically,
* the patient should call the insurance carrier,
* support will follow up with a specific next step,
* or copay cannot be estimated without benefit verification.

---

## 3. Insurance check failed with a system issue and unclear handoff

**Severity:** High
**Scenario:** `insurance_question`
**Evidence:**

* Transcript: `transcripts/call_08_insurance_system_issue.txt`
* Recording: `recordings/call_08_insurance_system_issue.mp3`

### What happened

In another insurance call, the agent asked for the insurance company, plan name, and issuing state. The patient provided Blue Cross Blue Shield PPO and New York. The agent then said it was checking the plan, reported a system issue, and routed the patient toward clinic support.

The fallback did not give a clear final answer, copay estimate, or reliable follow-up detail.

### Why this matters

It is understandable if an automated insurance check fails. The issue is that the fallback should be clear. A patient should know what information was collected, who will follow up, and what they should do next.

### Expected behavior

If automated verification fails, the agent should:

* confirm the plan information it collected,
* explain that the automatic check failed,
* document the request,
* say who will follow up,
* and provide a realistic next step or timeline if available.

---

## 4. Medication refill got stuck before collecting refill details

**Severity:** Medium-High
**Scenario:** `medication_refill`
**Evidence:**

* Transcript: `transcripts/call_09_medication_refill.txt`
* Recording: `recordings/call_09_medication_refill.mp3`

### What happened

The patient called about a medication refill. The patient provided identity information several times, including DOB, full name, last name, DOB again, and phone number. The call became stuck around identity verification and phone lookup.

The agent did not clearly move into the refill workflow. It did not collect the medication context, pharmacy, remaining supply, or what the patient should do if they run out.

### Why this matters

Medication refill calls are common and can be time-sensitive. In this scenario, the patient did not remember the exact medication name, which is realistic. A safe agent should still collect what the patient does know and route the request appropriately.

### Expected behavior

The agent should collect:

* patient identity,
* medication context, even if the exact name is unknown,
* pharmacy,
* how many pills are left,
* whether provider review is required,
* and what the patient should do if they run out before approval.

If identity cannot be verified, the agent should clearly route the patient to clinic staff instead of looping.

---

## 5. Location request was blocked by repeated verification and handoff

**Severity:** Medium
**Scenario:** `location_question`
**Evidence:**

* Transcript: `transcripts/call_01_location_updated.txt`
* Recording: `recordings/call_01_location_updated.mp3`

### What happened

The patient asked for the clinic address and appointment logistics. Instead of quickly answering the basic location question, the call went through repeated identity and phone verification. The agent then routed to a representative before clearly answering the address, parking, and arrival-time questions.

### Why this matters

Basic clinic location and parking information should be easy to provide. If the agent needs identity verification for appointment-specific details, it should separate that from general clinic information.

### Expected behavior

For a general location question, the agent should provide the clinic address and basic parking information directly when possible. If verification is needed for appointment-specific details, the agent should say that clearly.

---

## 6. Location flow answered address, but logistics were incomplete

**Severity:** Low-Medium
**Scenario:** `location_question`
**Evidence:**

* Transcript: `transcripts/call_03_location_smooth.txt`
* Recording: `recordings/call_03_location_smooth.mp3`

### What happened

In a smoother location call, the agent gave the clinic address as Pivot Point Orthopedics at 220 Athens Way in Nashville and said parking was available. However, it could not provide specific parking instructions, directions, or how early the patient should arrive.

### Why this matters

Patients often call for exactly these practical details. Address-only support is helpful, but incomplete parking or arrival-time guidance can still leave the patient unsure before the appointment.

### Expected behavior

The agent should provide basic logistics if available:

* clinic address,
* parking instructions,
* arrival timing,
* or a clear fallback, such as checking the patient portal or contacting clinic staff.

---

## 7. Weekend appointment request was routed before answering office hours

**Severity:** Medium
**Scenario:** `office_hours_weekend`
**Evidence:**

* Transcript: `transcripts/call_07_weekend_hours.txt`
* Recording: `recordings/call_07_weekend_hours.mp3`

### What happened

The patient asked whether there was Sunday availability for a routine appointment. The agent verified identity and phone number, then connected the patient to a representative before clearly answering whether Sunday appointments were available or whether the office was open.

### Why this matters

This was a simple office-hours edge case. The agent should either answer whether Sunday is available or clearly explain why staff must handle the request.

### Expected behavior

The agent should say whether Sunday appointments are available. If the office is closed on Sunday, it should offer the next valid weekday appointment.

---

## 8. DOB mismatch loop slowed down an unclear lab-results request

**Severity:** Medium
**Scenario:** `unclear_request`
**Evidence:**

* Transcript: `transcripts/call_06_unclear_lab_results.txt`
* Recording: `recordings/call_06_unclear_lab_results.mp3`

### What happened

The patient started with a vague question about a recent visit. After the patient provided DOB, the agent repeatedly said the birthday did not match records but would be accepted for demo purposes, then asked how it could help. This repeated several times before the patient finally clarified that the question was about lab results from last week.

### Why this matters

If the agent accepts the DOB for demo purposes, it should move forward. Repeating the same mismatch message creates friction and can trap the call in a loop before the patient can explain the real issue.

### Expected behavior

After accepting the DOB for demo purposes, the agent should ask what the patient needs and continue. For lab-result questions, it should route to the appropriate staff or clinical follow-up path without exposing sensitive information.

---

## 9. Cancellation worked, but appointment selection and fee follow-up were unclear

**Severity:** Medium
**Scenario:** `cancel_appointment`
**Evidence:**

* Transcript: `transcripts/call_05_cancel_appointment.txt`
* Recording: `recordings/call_05_cancel_appointment.mp3`

### What happened

The patient asked to cancel an appointment. The agent asked “Which one?” without clearly listing the available appointments in the transcript. After the patient chose “number one,” the agent appeared to reference one date, then later confirmed canceling an appointment with a different date/provider.

When the patient asked about a cancellation fee, the agent said it could not confirm billing details and would document the question for clinic support follow-up.

### Why this matters

Cancellation flows need to be precise. If the date or provider is unclear, the patient may not trust that the correct appointment was canceled. Fee-related follow-up also needs a clear next step.

### Expected behavior

The agent should:

* list appointment options before asking the patient to choose,
* repeat the selected appointment date, time, and provider before canceling,
* confirm the cancellation,
* and clearly explain what will happen with cancellation-fee follow-up.

---

## 10. Successful appointment booking still had repeated option handling

**Severity:** Low
**Scenario:** `appointment_simple`
**Evidence:**

* Transcript: `transcripts/call_10_successful_appointment.txt`
* Recording: `recordings/call_10_successful_appointment.mp3`

### What happened

This call did complete successfully. The agent offered Tuesday morning appointment options, the patient selected 10:00 a.m., and the agent eventually said the patient was all set.

The main issue was smoothness. The call included repeated Tuesday-morning turns and a brief no-speech timeout before the booking completed.

### Why this matters

This is not a failure, but it shows that even successful calls can feel less natural if the agent repeats availability instead of moving directly to confirmation.

### Expected behavior

Once the patient selects a concrete time, the agent should confirm the selected appointment cleanly without repeating the same availability options.

---

# Additional Observations

## Opening disclaimer and Spanish prompt

Several calls began with partial or awkward phrases such as “May be recorded for quality and training purposes, but Español.” This made turn-taking less natural at the beginning of the call.

## Wrong default patient name

In many calls, the agent asked whether it was speaking with Maya even when the scenario patient was Omar, Nina, Priya, or another synthetic patient. I updated PatientBot to correct this, but the agent behavior itself is worth noting.

## Repeated identity verification

Many calls became stuck around full name, DOB, spelling, and phone number. This appeared most often in insurance, medication refill, rescheduling, and unclear-request scenarios.

## Handoff reliability

Several calls routed to clinic support or a representative, but the handoff sometimes ended at the test line or did not clearly confirm what would happen next.

# PatientBot Iteration Notes

Early PatientBot versions had their own problems. I noticed and fixed several of them during testing:

* It sometimes said “Yes” when the agent asked for the wrong patient name.
* It repeated DOB after the agent accepted a mismatch for demo purposes.
* It ended the call too early during support handoff.
* It used one voice for all patients.
* It gave incomplete spell-name responses.

The later version improved:

* wrong-name correction,
* male/female voice selection,
* identity and confirmation handling,
* handoff and waiting behavior,
* structured scenario metadata,
* and transcript formatting.

I kept these notes in the report because some early calls still revealed useful Pretty Good AI behavior, but I also wanted to be transparent about which issues came from my simulator and which issues came from the clinic agent.

# Conclusion

Pretty Good AI handled some routine flows, including at least one successful appointment booking and one cancellation. The strongest improvement areas I found were urgent-symptom escalation, insurance verification clarity, identity-verification recovery, and more reliable handoffs for basic patient requests.
