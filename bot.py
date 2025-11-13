import logging
import re
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("7923783708:AAFw9p-sBGOe0n_jVMGFx1icIbAg4zfYDKA")
if not OPENAI_API_KEY:
    raise ValueError("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")

# OpenRouter uchun to'g'ri sozlamalar
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com",  # O'zingizning website manzilingiz
        "X-Title": "Telegram AI Assistant"
    }
)

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

user_context = {}
HISTORY_LIMIT = 10

# OpenRouter-da mavjud va ishlaydigan modellar
CURRENT_MODEL = "deepseek/deepseek-chat"  # Asosiy model

@dp.message(Command('start'))
async def start(message: types.Message):
    user_id = message.from_user.id
    user_context[user_id] = []
    await message.answer(
        "🤖 **Assalomu alaykum! Men AI yordamchiman**\n\n"
        "Menga istalgan savol berishingiz mumkin. Men sizga yordam berishga harakat qilaman!\n\n"
        "📝 **Foydali buyruqlar:**\n"
        "/clear - suhbat tarixini tozalash\n"
        "/models - mavjud modellarni ko'rish\n"
        "/help - yordam"
    )

@dp.message(Command('help'))
async def help_command(message: types.Message):
    help_text = """
🆘 **Yordam**

Men OpenRouter API orqali ishlaydigan sun'iy intellekt yordamchiman.

**Buyruqlar:**
/start - botni ishga tushirish
/clear - suhbat tarixini tozalash  
/models - mavjud modellarni ko'rish
/help - yordam

**Qanday ishlaydi:**
- Menga istalgan savol bering
- Men 10 ta oxirgi xabarni eslab qolaman
- Har bir yangi suhbat yangi tarix bilan boshlanadi
    """
    await message.answer(help_text)

@dp.message(Command('models'))
async def show_models(message: types.Message):
    models_text = """
🤖 **Mavjud Modellar:**

🔹 **DeepSeek:**
- `deepseek/deepseek-chat` - Asosiy model
- `deepseek/deepseek-coder` - Dasturlash uchun

🔹 **Meta:**
- `meta-llama/llama-3.1-8b-instruct` - Llama 3.1
- `meta-llama/llama-3-8b-instruct` - Llama 3

🔹 **Google:**
- `google/gemma-2-9b-it` - Gemma 2
- `google/gemma-7b-it` - Gemma

🔹 **Microsoft:**
- `microsoft/wizardlm-2-8x22b` - WizardLM

🔹 **OpenAI:**
- `openai/gpt-3.5-turbo` - GPT-3.5 Turbo

🔄 Modelni o'zgartirish uchun /change_model buyrug'idan foydalaning
    """
    await message.answer(models_text)

@dp.message(Command('change_model'))
async def change_model(message: types.Message):
    # Soddalashtirilgan model tanlash
    models_keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="deepseek/deepseek-chat")],
            [types.KeyboardButton(text="meta-llama/llama-3.1-8b-instruct")],
            [types.KeyboardButton(text="google/gemma-2-9b-it")],
            [types.KeyboardButton(text="openai/gpt-3.5-turbo")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "🔄 Modelni tanlang:",
        reply_markup=models_keyboard
    )

@dp.message(Command('clear'))
async def clear_history(message: types.Message):
    user_id = message.from_user.id
    user_context[user_id] = []
    await message.answer("✅ Suhbat tarixi tozalandi.")

@dp.message(lambda message: message.text and any(model in message.text for model in [
    "deepseek/deepseek-chat", 
    "meta-llama/llama-3.1-8b-instruct",
    "google/gemma-2-9b-it",
    "openai/gpt-3.5-turbo"
]))
async def handle_model_selection(message: types.Message):
    global CURRENT_MODEL
    user_id = message.from_user.id
    new_model = message.text
    
    CURRENT_MODEL = new_model
    user_context[user_id] = []  # Yangi model uchun tarixni tozalash
    
    await message.answer(
        f"✅ Model o'zgartirildi: `{new_model}`\n"
        f"Suhbat tarixi yangilandi.",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_message = message.text
    
    if not user_message or not user_message.strip():
        await message.answer("Iltimos, matnli xabar yuboring.")
        return
        
    logger.info(f"Foydalanuvchi {user_id}: {user_message}")

    if user_id not in user_context:
        user_context[user_id] = []

    user_context[user_id].append({"role": "user", "content": user_message})

    if len(user_context[user_id]) > HISTORY_LIMIT:
        user_context[user_id] = user_context[user_id][-HISTORY_LIMIT:]

    try:
        # So'rovni yuborish
        completion = await client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=user_context[user_id],
            max_tokens=2000,
            temperature=0.7,
            stream=False
        )

        if completion and completion.choices:
            choice = completion.choices[0]
            content = choice.message.content
            
            if content:
                # HTML teglarni tozalash
                cleaned_content = re.sub(r'<.*?>', '', content).strip()

                if cleaned_content:
                    # Telegram xabar chegarasi (4096 belgi)
                    if len(cleaned_content) > 4000:
                        chunks = [cleaned_content[i:i+4000] for i in range(0, len(cleaned_content), 4000)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await message.answer(f"**Javob:**\n\n{chunk}")
                            else:
                                await message.answer(chunk)
                    else:
                        await message.answer(f"**Javob:**\n\n{cleaned_content}")
                    
                    # Tarixga qo'shish
                    user_context[user_id].append({"role": "assistant", "content": cleaned_content})
                    
                    logger.info(f"Foydalanuvchi {user_id} ga javob yuborildi")
                else:
                    await message.answer("❌ Neyrotarmoq bo'sh javob qaytardi.")
            else:
                await message.answer("❌ Neyrotarmoqdan javob olinmadi.")
        else:
            await message.answer("❌ Neyrotarmoq bilan bog'lanishda xatolik.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Xato: {error_msg}")
        
        # Turlicha xatoliklar uchun
        if "404" in error_msg or "No endpoints" in error_msg:
            await message.answer(
                f"❌ Model topilmadi: `{CURRENT_MODEL}`\n\n"
                f"Iltimos, /change_model buyrug'i orqali boshqa model tanlang."
            )
        elif "401" in error_msg or "auth" in error_msg.lower():
            await message.answer("❌ API kaliti noto'g'ri yoki muddati o'tgan.")
        elif "429" in error_msg:
            await message.answer("⏳ So'rovlar chegarasiga yetildi. Iltimos, biroz kuting.")
        else:
            await message.answer(f"❌ Xatolik yuz berdi: {error_msg}")

async def main():
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())