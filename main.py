import telebot
from telebot.types import InlineKeyboardMarkup
from telebot.types import InlineKeyboardButton
from config.settings import API_TOKEN
from API.api import fetch_jobs, extract_all_skills
from bot.formater import format_project
from bot.user_data import *
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

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

/skills

/reset
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
@bot.message_handler(commands=["skills"])
def skills(message):

    data=fetch_jobs("")

    projects=data["data"]["data"]

    skills=extract_all_skills(projects)

    keyboard=InlineKeyboardMarkup(row_width=2)

    for skill in skills[:30]:

        keyboard.add(

            InlineKeyboardButton(

                skill,

                callback_data=f"skill:{skill}"

            )

        )

    keyboard.add(

        InlineKeyboardButton(

            "✅ پایان انتخاب",

            callback_data="finish"

        )
    )

    bot.send_message(

        message.chat.id,

        "حداکثر سه مهارت را انتخاب کنید.",

        reply_markup=keyboard
    )



@bot.message_handler(commands=["reset"])
def reset(message):

    reset_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        """
✅ تمام تنظیمات شما حذف شد.

دوباره از ابتدا شروع کنید.

ابتدا مهارت‌های خود را انتخاب کنید:

/skills
"""
    )

@bot.message_handler(func=lambda message: message.text == "🔄 شروع مجدد")
def reset(message):

    reset_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "✅ اطلاعات شما پاک شد.\nدوباره از /skills شروع کنید."
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
    projects = data["data"]["data"]

    selected = get_skills(message.from_user.id)

    for project in projects:

        project_skills = [
            skill["name"].lower()
            for skill in project["skills"]
        ]

        # اگر کاربر Skill انتخاب کرده باشد
        if selected:

            if not any(
                    skill.lower() in project_skills
                    for skill in selected
            ):
                continue

        bot.send_message(
            message.chat.id,
            format_project(project)
        )

        #return

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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.add(
        KeyboardButton("🔄 شروع مجدد")
    )

    bot.send_message(
        message.chat.id,
        "اگر می‌خواهید جستجوی جدیدی انجام دهید، روی دکمه زیر بزنید.",
        reply_markup=keyboard
    )
@bot.callback_query_handler(func=lambda call:True)

def callback(call):

    user_id=call.from_user.id

    create_user(user_id)

    if call.data=="finish":

        bot.edit_message_text(

            f"""

مهارت های انتخاب شده:

{get_skills(user_id)}

""",

            call.message.chat.id,

            call.message.message_id

        )

        return

    if call.data.startswith("skill:"):

        skill=call.data.split(":")[1]

        if len(get_skills(user_id))>=3:

            bot.answer_callback_query(

                call.id,

                "حداکثر سه مهارت"

            )

            return

        add_skill(user_id,skill)

        bot.answer_callback_query(

            call.id,

            f"{skill} اضافه شد."
        )

bot.infinity_polling()

