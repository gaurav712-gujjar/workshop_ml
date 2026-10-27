import os 
import sys 
import uvicorn 
from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles 
from fastapi.templating import Jinja2Templates 
from src.exception import CustomException 
from src.logger import get_logger 
logger = get_logger(__name__) 
from src.pipeline.predict_pipeline import CustomData, PredictPipeline
from nlp_pretrained.ner_tagger import(get_pos_tags , extract_entities) 
from nlp_pretrained.embedding import (most_similar_words) 
from nlp_pretrained.sentiment_analyzer import analyze_sentiment 
from starlette.middleware.sessions import SessionMiddleware
from src.db import init_db
from src.auth.auth_utils import create_user, get_user_by_email, verify_password
import mysql.connector
from fastapi import UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from src.chatbot.chat_engine import get_chat_response, analyze_injury_photo
from src.chatbot.chat_engine import get_chat_response
from rag.rag_pipeline import RAGPipeline
from src.booking.booking_utils import (
    get_all_specializations, get_doctors_by_specialization,
    get_available_slots, book_slot, get_user_appointments,
    get_patient_context_summary, add_doctor, get_all_doctors,
    add_slot, get_all_slots, delete_doctor
)


app= FastAPI(title="Covid Prediction Clinic") 
app.add_middleware(SessionMiddleware, secret_key="change-this-to-a-random-secret-key")
init_db()

##mouting the css file 
app.mount("/static", StaticFiles(directory="static"), name="static") 

##Set the template folder 
templates = Jinja2Templates(directory="templates") 

# Initialize RAG pipeline
rag_pipeline = RAGPipeline()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    logger.info("Home page accessed...")
    return templates.TemplateResponse(request, "index.html")

async def home(request:Request):
    logger.info("Home page accessed...") 
    return templates.TemplateResponse(request, "index.html") 

@app.get("/predict", response_class=HTMLResponse)
async def predict_form(request: Request):
    logger.info("Predict form page accessed.....") 
    return templates.TemplateResponse(request, "predict.html", {"result":None}) 

@app.post("/predict", response_class=HTMLResponse)
async def predict_result(
    request: Request,
    age:int = Form(...),
    gender: str = Form(...),
    fever: float = Form(...),
    cough: str = Form(...),
    city: str = Form(...) 
) :
    try:
        logger.info(f"Prediction request received :: age{age}, gender{gender}, fever{fever}, cough{cough},city{city}")
        custom_data = CustomData(age=age,gender=gender,fever=fever,cough=cough,city=city)
        data_df = custom_data.get_data_as_dataframe() 
        predict_pipeline = PredictPipeline() 
        result , probability = predict_pipeline.predict(data_df) 
        return templates.TemplateResponse(
            request,
            "predict.html",
            {
                "result": result,
                "probability":probability,
                "form_data": {
                    "age":age,
                    "gender":gender,
                    "fever":fever,
                    "cough":cough,
                    "city":city
                }
            }
        )
    except Exception as e:
        raise CustomException(e,sys) 

@app.get("/health")
async def health_check():
    logger.info("Monitering alert....")
    return {"status":"ok"}


### NLP Pretrained 

@app.get("/pretrained-nlp" , response_class=HTMLResponse) 
async def pretrained_nlp_form(request: Request):
    return templates.TemplateResponse(request, 
                                      "pretrained_nlp.html",
                                      {
                                          "result": None,

                                          "form_data": {
                                              "query": ""
                                          },
                                          "error": None 
                                      })

@app.post("/pretrained-nlp" , response_class=HTMLResponse) 
async def pretrained_nlp_analysis(
    request: Request,
    query: str= Form(...)
):
    try:
        ## text clean 
        query = query.strip() 
        if not query:
            return templates.TemplateResponse(
                request,
                "pretrained_nlp.html",
                {
                    "result": None,
                    "form_data": {
                        "query": ""
                    },
                    "error": "Please enter some text..." 
                }
            )

        ## Pos tagging 
        pos_tags = get_pos_tags(query) 

        ## NER 
        entities = extract_entities(query) 

        ## Sentiment Analysis 
        sentiment = analyze_sentiment(query) 

        ## Word Embeddings 
        similar_words = [] 
        words = query.split() 
        first_word = words[0].lower() 
        if words:
            try:
                similar_words = most_similar_words(first_word , topn=5) 
            except Exception as e :
                logger.warning(f"Glove similarity failed for: " , {first_word} ,"and the error is:", {e}) 
                similar_words = [] 
        ## final result 
        result = {
            "query": query,
            "pos_tags": pos_tags,
            "entities": entities,
            "similar_words": similar_words,
            "sentiment": sentiment
        }
        ##render result 
        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": result,
                "form_data": {
                    "query": query
                },
                "error": None
            }
        )



    except Exception as e :
        logger.info("Error occured in pretrained nlp analysis")
        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": None,
                "form_data": {
                    "query": query
                },
                "error": str(e)
            }
        )
     

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    logger.info("Chat page accessed...")
    return templates.TemplateResponse(request, "chat.html")

@app.post("/chat/api")
async def chat_api(request: Request):
    body = await request.json()
    user_message = body.get("message", "").strip()
    history = body.get("history", [])

    if not user_message:
        return {"reply": "Please type something."}

    patient_context = None
    user_id = request.session.get("user_id")
    if user_id:
        patient_context = get_patient_context_summary(user_id)

    reply = get_chat_response(user_message, history, patient_context)

    specialist = None
    if "SPECIALIST:" in reply:
        parts = reply.split("SPECIALIST:")
        reply = parts[0].strip()
        specialist = parts[1].strip()

    return {"reply": reply, "specialist": specialist}

@app.post("/chat/photo")
async def chat_photo(request: Request, file: UploadFile = File(...)):
    image_bytes = await file.read()
    reply = analyze_injury_photo(image_bytes)

    specialist = None
    if "SPECIALIST:" in reply:
        parts = reply.split("SPECIALIST:")
        reply = parts[0].strip()
        specialist = parts[1].strip()

    return {"reply": reply, "specialist": specialist}


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "profile.html")

@app.get("/book", response_class=HTMLResponse)
async def book_page(request: Request, specialization: str = None):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    specializations = get_all_specializations()
    return templates.TemplateResponse(
        request, "book.html",
        {"specializations": specializations, "preselected": specialization}
    )

@app.get("/book/doctors")
async def book_doctors(request: Request, specialization: str):
    doctors = get_doctors_by_specialization(specialization)
    return {"doctors": doctors}

@app.get("/book/slots")
async def book_slots(request: Request, doctor_id: int):
    slots = get_available_slots(doctor_id)
    for s in slots:
        s["slot_date"] = str(s["slot_date"])
        s["slot_time"] = str(s["slot_time"])
    return {"slots": slots}

@app.post("/book/confirm")
async def book_confirm(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    doctor_id = int(form["doctor_id"])
    slot_id = int(form["slot_id"])
    reason = form.get("reason", "")
    success = book_slot(request.session["user_id"], doctor_id, slot_id, reason)
    if not success:
        return RedirectResponse("/book?error=slot_taken", status_code=303)
    return RedirectResponse("/appointments", status_code=303)

@app.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    appts = get_user_appointments(request.session["user_id"])
    return templates.TemplateResponse(request, "appointments.html", {"appointments": appts})
    

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")

@app.post("/register")
async def register_submit(request: Request):
    form = await request.form()
    name, email, password = form["name"], form["email"], form["password"]
    try:
        create_user(name, email, password)
    except mysql.connector.IntegrityError:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Email already registered"}
        )
    return RedirectResponse("/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    email, password = form["email"], form["password"]
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid email or password"})
    request.session["user_id"] = user["id"]
    request.session["user_name"] = user["name"]
    request.session["user_email"] = user["email"]
    request.session["is_admin"] = bool(user["is_admin"])   # <-- ye line add karo
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    doctors = get_all_doctors()
    slots = get_all_slots()
    return templates.TemplateResponse(request, "admin.html", {"doctors": doctors, "slots": slots})

@app.post("/admin/add-doctor")
async def admin_add_doctor(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    add_doctor(form["name"], form["specialization"])
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/add-slot")
async def admin_add_slot(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    form = await request.form()
    add_slot(int(form["doctor_id"]), form["slot_date"], form["slot_time"])
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/delete-doctor/{doctor_id}")
async def admin_delete_doctor(request: Request, doctor_id: int):
    if not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    delete_doctor(doctor_id)
    return RedirectResponse("/admin", status_code=303)


# ---------------- RAG CLINIC ASSISTANT ----------------

@app.get("/ask", response_class=HTMLResponse)
async def clinic_assistant_form(request: Request):
    logger.info("Clinic assistant (RAG) form page accessed")

    return templates.TemplateResponse(
        request,
        "clinic_assistant.html",
        {
            "result": None,
            "form_data": {"question": ""},
            "error": None
        }
    )


@app.post("/ask", response_class=HTMLResponse)
async def clinic_assistant_answer(
    request: Request,
    question: str = Form(...)
):
    logger.info(f"Clinic assistant question received: '{question}'")

    try:
        question = question.strip()

        if not question:
            return templates.TemplateResponse(
                request,
                "clinic_assistant.html",
                {
                    "result": None,
                    "form_data": {"question": ""},
                    "error": "Please enter a question."
                }
            )

        result = rag_pipeline.answer(question)

        return templates.TemplateResponse(
            request,
            "clinic_assistant.html",
            {
                "result": result,
                "form_data": {"question": question},
                "error": None
            }
        )

    except Exception as e:
        logger.exception("Error in RAG clinic assistant")
        raise CustomException(e, sys)


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)