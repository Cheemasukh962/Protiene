import os

from dotenv import load_dotenv


load_dotenv()


GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")
