import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

API_URL = "https://www.karlancer.com/api/publics/search/projects"

REQUEST_TIMEOUT = 10