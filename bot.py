import time
import threading
import os
from dotenv import load_dotenv
import telebot
from telebot.types import ReplyKeyboardMarkup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

load_dotenv()

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7977504618:AAHo-N5eUPKOGlklZUomqlhJ4-op3t68GSE")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID", "-1002311125652"))
IVASMS_EMAIL = os.getenv("IVASMS_EMAIL", "imdigitalvasu@gmail.com")
IVASMS_PASSWORD = os.getenv("IVASMS_PASSWORD", "@Vasu2412")
IVASMS_URL = "https://www.ivasms.com/login"
# ==================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
driver = None
acquired_numbers = []
monitoring = False

def start_browser():
    global driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def login_ivasms():
    driver.get(IVASMS_URL)
    
    # Wait for email field
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "email")))
    driver.find_element(By.NAME, "email").send_keys(IVASMS_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)

    # Wait for login button and click
    try:
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
        )
        login_btn.click()
    except Exception as e:
        print("❌ Login button not found or not clickable.")
        print(e)
        # Take screenshot to debug
        driver.save_screenshot("login_error.png")


def get_available_numbers():
    driver.get("https://www.ivasms.com/test-number")
    time.sleep(3)
    numbers = []
    rows = driver.find_elements(By.XPATH, "//table//tr")
    for row in rows[1:]:
        cols = row.find_elements(By.TAG_NAME, "td")
        if cols:
            country = cols[0].text.strip()
            number = cols[1].text.strip()
            numbers.append(f"{country} {number}")
    return numbers

def acquire_all_numbers():
    driver.get("https://www.ivasms.com/test-number")
    time.sleep(3)
    buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Acquire')]")
    for btn in buttons:
        try:
            btn.click()
            time.sleep(1)
        except:
            continue

def check_for_otps():
    while True:
        try:
            driver.get("https://www.ivasms.com/client-active-sms")
            time.sleep(3)
            messages = driver.find_elements(By.XPATH, "//table//tr")
            for msg in messages[1:]:
                cols = msg.find_elements(By.TAG_NAME, "td")
                if cols and "OTP" in cols[2].text:
                    number = cols[0].text.strip()
                    content = cols[2].text.strip()
                    try:
                        bot.send_message(YOUR_TELEGRAM_ID, f"📩 OTP for {number}: {content}")
                    except Exception as e:
                        print(f"[!] Error sending OTP to Telegram: {e}")
        except Exception as e:
            print("[!] Error checking OTPs:", e)
        time.sleep(60)

@bot.message_handler(commands=['start'])
def handle_start(message):
    global monitoring, acquired_numbers

    try:
        bot.reply_to(message, "🔄 Logging into iVASMS...")
    except Exception as e:
        print(f"[!] Failed to reply: {e}")

    try:
        start_browser()
        login_ivasms()
        numbers = get_available_numbers()

        if not numbers:
            bot.send_message(message.chat.id, "❌ No numbers available.")
            return

        acquired_numbers = numbers

        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add("yes", "no")

        bot.send_message(
            message.chat.id,
            f"Hey Teez Plug Bot is active. Do you want to acquire these numbers?\n\n{', '.join(numbers)}",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Something went wrong: {e}")
        print(f"[!] Error in /start: {e}")

@bot.message_handler(func=lambda message: message.text.lower() in ["yes", "no"])
def handle_response(message):
    global monitoring, acquired_numbers

    if message.text.lower() == "yes":
        try:
            acquire_all_numbers()
            bot.send_message(message.chat.id, "✅ Numbers acquired. Monitoring for OTPs...")
            if not monitoring:
                monitoring = True
                threading.Thread(target=check_for_otps, daemon=True).start()
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error acquiring numbers: {e}")
    else:
        bot.send_message(message.chat.id, "❌ Okay, cancelled.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "/start - Start the bot\n/help - Show help info")

print("🤖 Bot is running...")
if __name__ == '__main__':
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"[!] Polling crashed: {e}")
