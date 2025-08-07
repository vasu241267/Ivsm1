import time
import threading
from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import logging

# === CONFIG ===
TELEGRAM_TOKEN = "8011551620:AAFvDlRL7brL1JF9kEpQJXIVzZf01og4Lc0"
YOUR_TELEGRAM_ID = 6972264549
IVASMS_EMAIL = "imdigitalvasu@gmail.com"
IVASMS_PASSWORD = "@Vasu2412"
IVASMS_URL = "https://www.ivasms.com/login"
# ==============

app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)
driver = None
acquired_numbers = []
monitoring = False

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

@app.route('/')
def health_check():
    return "✅ Bot is running", 200

def start_browser():
    global driver
    log.info("🧪 Starting headless browser...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    log.info("✅ Browser started")

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def login_ivasms():
    try:
        log.info("🔐 Logging into iVASMS...")
        driver.get(IVASMS_URL)

        wait = WebDriverWait(driver, 15)

        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(IVASMS_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(IVASMS_PASSWORD)

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]")))
        login_button.click()

        # Confirm dashboard is loaded (adjust if needed)
        wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Test Numbers')]")))

        log.info("✅ Logged in successfully.")
    except Exception as e:
        log.error(f"❌ Login failed: {e}")
        try:
            driver.save_screenshot("/app/login_error.png")
            log.info("📸 Screenshot saved to /app/login_error.png")
        except:
            log.warning("⚠ Could not save screenshot.")

def get_available_numbers():
    log.info("🔍 Fetching available numbers...")
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
    log.info(f"📞 Found {len(numbers)} numbers.")
    return numbers

def acquire_all_numbers():
    log.info("🛠 Acquiring numbers...")
    driver.get("https://www.ivasms.com/test-number")
    time.sleep(3)
    buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Acquire')]")
    for btn in buttons:
        try:
            btn.click()
            time.sleep(1)
        except:
            continue
    log.info("✅ All numbers acquired.")

def check_for_otps():
    log.info("🔁 Started OTP monitoring thread.")
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
                    bot.send_message(YOUR_TELEGRAM_ID, f"📩 OTP for {number}: {content}")
                    log.info(f"📩 OTP for {number}: {content}")
        except Exception as e:
            log.error(f"❌ Error checking OTPs: {e}")
        time.sleep(60)

@bot.message_handler(commands=['start'])
def handle_start(message):
    global monitoring, acquired_numbers

    bot.reply_to(message, "🔄 Logging into iVASMS...")
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

@bot.message_handler(func=lambda message: message.text.lower() in ["yes", "no"])
def handle_response(message):
    global monitoring, acquired_numbers

    if message.text.lower() == "yes":
        acquire_all_numbers()
        bot.send_message(message.chat.id, "✅ Numbers acquired. Monitoring for OTPs...")
        if not monitoring:
            monitoring = True
            threading.Thread(target=check_for_otps, daemon=True).start()
    else:
        bot.send_message(message.chat.id, "❌ Okay, cancelled.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.reply_to(message, "/start - Start the bot\n/help - Show help info")

# Run the bot in a separate thread so Flask healthcheck stays responsive
def run_bot():
    try:
        log.info("🚀 Bot polling started...")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        log.error(f"Bot polling crashed: {e}")

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)  # Render listens on port 10000
