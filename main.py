import telebot

from config import API_TOKEN
from API.api import fetch_jobs
from bot.formater import format_project
from bot.user_data import *

bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=["start"])
def start(message):

    create_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        """
سلام 👋

به Job Matcher خوش آمدید.

دستورات:

/help

/settings

کافی است نام مهارت را ارسال کنید.
"""
    )


@bot.message_handler(commands=["help"])
def help_command(message):

    bot.send_message(
        message.chat.id,
        """
راهنما

برای جستجو:

python

django

react

telegram

برای تنظیم حداقل بودجه:

/settings
"""
    )


@bot.message_handler(commands=["settings"])
def settings(message):

    create_user(message.from_user.id)

    set_state(message.from_user.id, "WAITING_FOR_BUDGET")

    bot.send_message(
        message.chat.id,
        "حداقل بودجه موردنظر را وارد کنید."
    )


@bot.message_handler(func=lambda message: True)
def all_messages(message):

    create_user(message.from_user.id)

    state = get_state(message.from_user.id)

    # ---------- Budget ----------

    if state == "WAITING_FOR_BUDGET":

        if not message.text.isdigit():

            bot.send_message(
                message.chat.id,
                "فقط عدد وارد کنید."
            )

            return

        budget = int(message.text)

        set_budget(
            message.from_user.id,
            budget
        )

        set_state(
            message.from_user.id,
            "NORMAL"
        )

        bot.send_message(
            message.chat.id,
            f"""
✅ حداقل بودجه روی {budget} تنظیم شد.
"""
        )

        return

    # ---------- Search ----------

    data = fetch_jobs(message.text)

    if data is None:

        bot.send_message(
            message.chat.id,
            "ارتباط با API برقرار نشد."
        )

        return

    projects = data["data"]["data"]

    if not projects:

        bot.send_message(
            message.chat.id,
            "پروژه‌ای پیدا نشد."
        )

        return

    min_budget = get_budget(message.from_user.id)

    count = 0

    for project in projects:

        budget = project["max_budget"] or 0

        if budget < min_budget:

            continue

        bot.send_message(
            message.chat.id,
            format_project(project)
        )

        count += 1

    if count == 0:

        bot.send_message(
            message.chat.id,
            "هیچ پروژه‌ای با بودجه موردنظر پیدا نشد."
        )


bot.infinity_polling()