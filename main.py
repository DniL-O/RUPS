import telebot
import requests
from threading import Thread
from time import sleep
from fake_useragent import UserAgent
import settings
import schedule
from threading import Thread
from time import sleep
import datetime

if __name__ == '__main__':
    bot = telebot.TeleBot(settings.TOKEN, parse_mode="HTML")
    ua = UserAgent()
    keyboard_time = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for btn in settings.BUTTONS.keys():
        keyboard_time.add(btn)
    hideBoard = telebot.types.ReplyKeyboardRemove()

def save_data(data, path):
    file = open(path, "w")
    for user in data.keys():
        file.write(f"{user};{users[user][0]};{data[user][1]};{data[user][2]};\n")
    file.close()

def load_data(path):
    file = open(path, "r")
    data = {}
    for line in file.readlines():
        user = line.split(";")
        data[user[0]] = [user[1], user[2], user[3]]
    return data

def schedule_checker():
    while True:
        try:
            schedule.run_pending()
            sleep(30)
        except Exception:
            pass

def check_schedules():
    now = datetime.datetime.now()
    if schedule.get_jobs():
        for job in schedule.get_jobs():
            schedule.cancel_job(job)
    for user in users.keys():
        send_time = datetime.datetime.strptime(users[user][1], settings.TIME_FORMAT)
        if now >= send_time:
            users[user][1] = now.strftime(settings.TIME_FORMAT)
            send_weather(user, users[user][0])
        else:
            schedule.every().day.at(send_time.strftime("%H:%M")).do(send_weather, user, users[user][0])

@bot.message_handler(commands=["start"])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, "Здравствуйте! Я бот для регулярного получения прогноза погоды. Прогноз какого города вас интересует?")
    bot.register_next_step_handler(msg, validate_city)

def validate_city(message):
    weather_data = requests.get("https://api.openweathermap.org/data/2.5/weather", headers={"User-Agent": ua.random}, params={"q": message.text, "appid": settings.OW_API}).json()
    if weather_data["cod"] == "404":
        msg = bot.send_message(message.chat.id, "Такого города нет, попробуйте снова")
        bot.register_next_step_handler(msg, validate_city)
    elif weather_data["cod"] == 200:
        msg = bot.send_message(message.chat.id, "Как часто отправлять вам прогноз?", reply_markup=keyboard_time)
        bot.register_next_step_handler(msg, ask_time, city=message.text)

def ask_time(message, city):
    if message.text in settings.BUTTONS.keys():
        now = datetime.datetime.now()
        users[str(message.chat.id)] = [city, now.strftime(settings.TIME_FORMAT), settings.BUTTONS[message.text]]
        save_data(users, "users.txt")
        send_weather(message.chat.id, city)
    else:
        msg = bot.send_message(message.chat.id, "Выберите из предложенных ниже вариантов")
        bot.register_next_step_handler(msg, ask_time, city=city)

def time_work(chat_id):
    chat_id = str(chat_id)
    send_time = (datetime.datetime.strptime(users[chat_id][1], settings.TIME_FORMAT) + datetime.timedelta(minutes=int(users[chat_id][2])))
    users[chat_id][1] = send_time.strftime(settings.TIME_FORMAT)
    save_data(users, "users.txt")
    schedule.every().day.at(send_time.strftime("%H:%M")).do(send_weather, chat_id, users[chat_id][0])

def send_weather(chat_id, city):
    if str(chat_id) in users.keys():
        weather_data = requests.get("https://api.openweathermap.org/data/2.5/weather", headers={"User-Agent": ua.random}, params={"q": city, "appid": settings.OW_API, "lang": "ru", "units": "metric"}).json()
        temp = weather_data["main"]["temp"]
        desc = weather_data["weather"][0]["description"]
        humidity = weather_data["main"]["humidity"]
        pressure = weather_data["main"]["pressure"]
        speed = weather_data["wind"]["speed"]

        bot.send_message(chat_id, f"Погода {city}:\nТемпература: {temp}\U000000B0С, {desc}\nДавление: {pressure} мм рт. ст.\nВлажность: {humidity}%\nВетер: {speed} м/c", reply_markup=hideBoard)
        time_work(chat_id)
    return schedule.CancelJob

if __name__ == '__main__':
    users = load_data("users.txt")
    schedule_thread = Thread(target=schedule_checker)
    check_schedules()
    schedule_thread.start()
    bot.infinity_polling()
