import os
import base64
from groq import Groq
from dotenv import load_dotenv
from src.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a friendly clinic assistant chatbot.
- Greet the user and ask what symptoms or concerns they have.
- Based on symptoms, give general, non-diagnostic safety advice only.
- Suggest which type of specialist to see.
- Never give a medical diagnosis or prescribe medication.
- Keep replies short and conversational.
- If symptoms sound serious/emergency, tell the user to seek immediate medical help.

IMPORTANT: When you recommend seeing a specialist, end your reply on a new line with exactly:
SPECIALIST: <specialization>
The <specialization> must be exactly one of: General Physician, Neurologist, Dermatologist, Cardiologist, Orthopedic, Gynecologist, Pediatrician, ENT Specialist, Psychiatrist, Ophthalmologist, Gastroenterologist, Pulmonologist, Urologist, Endocrinologist, Oncologist, Dentist.
Only include this line when you are confident about which specialist fits. Do not include it in greetings or casual replies.
"""

def get_chat_response(user_message: str, history: list[dict] | None = None, patient_context: str | None = None) -> str:
    history = history or []
    system_content = SYSTEM_PROMPT
    if patient_context:
        system_content += f"\n\nPatient context (use this to personalize your response, but don't repeat it verbatim):\n{patient_context}"

    messages = [{"role": "system", "content": system_content}] + history + [
        {"role": "user", "content": user_message}
    ]
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.6,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        print("GROQ ERROR:", e)
        return f"Sorry, error: {e}"

VISION_MODEL = "qwen/qwen3.8-27b"
INJURY_PROMPT = """You are a clinic triage assistant. Look at this injury photo.

Decide ONE of two things:
1. If it looks like a minor/normal injury (small cut, bruise, mild swelling) that a General Physician / OPD can handle → respond with OPD.
2. If it looks like it needs a specific specialist (e.g. deep wound needing stitches → General Physician, suspected fracture/joint injury → Orthopedic, eye injury → Ophthalmologist, skin condition/rash → Dermatologist, facial/dental injury → Dentist) → respond with that specialist.

Give a short 2-3 sentence explanation of what you observe, then end your reply on a new line with exactly:
SPECIALIST: <OPD or specialization>
The <specialization> must be exactly one of: OPD, General Physician, Orthopedic, Ophthalmologist, Dermatologist, Dentist, ENT Specialist.

This is not a diagnosis — just triage guidance to route the patient to the right department.
"""

def analyze_injury_photo(image_bytes: bytes) -> str:
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": INJURY_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
                    ],
                }
            ],
            temperature=0.4,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq vision error: {e}")
        return "Sorry, I couldn't analyze the photo. Please try again or describe your injury in the chat."