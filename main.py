import os

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# --- CONFIG ---
# In production, use os.environ.get("KEY")
MONGO_URI = "YOUR_MONGODB_STRING_HERE"
GEMINI_KEY = "YOUR_GEMINI_KEY_HERE"

app = FastAPI()

# Allow your Frontend (Vercel) to talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all. In prod, put your Vercel URL here.
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup DB & AI
client = MongoClient(MONGO_URI)
db = client["english_course"]
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


# --- DATA MODELS ---
class UserLogin(BaseModel):
    user_id: int
    first_name: str


class ChatRequest(BaseModel):
    message: str
    context: str  # Current lesson text


# --- ENDPOINTS ---


@app.get("/")
def read_root():
    return {"status": "Server is running"}


@app.post("/login")
def login(user: UserLogin):
    # Check if user exists, if not create them
    existing = db.users.find_one({"user_id": user.user_id})
    if not existing:
        db.users.insert_one(
            {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "xp": 0,
                "current_lesson": 1,
                "status": "free",
            }
        )
        return {"msg": "New user created", "data": {"current_lesson": 1}}
    return {
        "msg": "Welcome back",
        "data": {"current_lesson": existing["current_lesson"]},
    }


@app.get("/lesson/{lesson_id}")
def get_lesson(lesson_id: int):
    # Fetch lesson content from DB
    lesson = db.lessons.find_one({"id": lesson_id}, {"_id": 0})
    if not lesson:
        # Fallback dummy data if DB is empty
        return {
            "id": 1,
            "title": "Introduction to Present Simple",
            "video_url": "https://www.w3schools.com/html/mov_bbb.mp4",  # Replace with your Telegram file link or YouTube
            "content": "We use Present Simple for habits.",
        }
    return lesson


@app.post("/ask-ai")
def ask_ai(req: ChatRequest):
    prompt = f"Context: {req.context}. \nStudent asks: {req.message}. \nAnswer briefly as a teacher."
    try:
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except:
        return {"reply": "My brain is tired. Try again!"}
