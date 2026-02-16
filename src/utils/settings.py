from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

DB_PORT = os.getenv("DB_PORT")
DB_HOST = os.getenv("DB_HOST")
DB_PASS = os.getenv("DB_PASS")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SERVER_AI_URL = os.getenv("SERVER_AI_URL")

