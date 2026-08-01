import requests
from config import API_URL, REQUEST_TIMEOUT


def fetch_jobs(query):

    try:

        response = requests.get(
            API_URL,
            params={"q": query},
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException:

        return None