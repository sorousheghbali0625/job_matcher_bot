import requests
from config.settings import API_URL, REQUEST_TIMEOUT


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

def extract_all_skills(projects):

    result=set()

    for project in projects:

        for skill in project["skills"]:

            result.add(skill["name"])

    return sorted(result)