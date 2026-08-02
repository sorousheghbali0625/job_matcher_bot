users = {}


def create_user(user_id):

    if user_id not in users:

        users[user_id] = {
            "state": "NORMAL",
            "min_budget": 0,
            "selected_skills": []
        }


def reset_user(user_id):
    users[user_id] = {
        "state": "NORMAL",
        "min_budget": 0,
        "selected_skills": []
    }


def set_state(user_id, state):

    users[user_id]["state"] = state


def get_state(user_id):

    return users[user_id]["state"]


def set_budget(user_id, budget):

    users[user_id]["min_budget"] = budget


def get_budget(user_id):

    return users[user_id]["min_budget"]


def add_skill(user_id, skill):

    skills = users[user_id]["selected_skills"]

    if skill not in skills and len(skills) < 3:

        skills.append(skill)


def remove_skill(user_id, skill):

    users[user_id]["selected_skills"].remove(skill)


def get_skills(user_id):

    return users[user_id]["selected_skills"]


def clear_skills(user_id):

    users[user_id]["selected_skills"]=[]
