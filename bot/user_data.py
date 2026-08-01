users = {}


def create_user(user_id):

    if user_id not in users:

        users[user_id] = {
            "state": "NORMAL",
            "min_budget": 0
        }


def set_state(user_id, state):

    users[user_id]["state"] = state


def get_state(user_id):

    return users[user_id]["state"]


def set_budget(user_id, budget):

    users[user_id]["min_budget"] = budget


def get_budget(user_id):

    return users[user_id]["min_budget"]