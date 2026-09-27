import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8937045240:AAEnwUIXkIG2lAqe4Xqcq5ybBbLvtNl1bjU"
ADMIN_ID = 7924604086  # Ваш Telegram ID (узнать можно в @userinfobot)

# Цены в Stars (XTR). Минимальная цена — 1 звезда.
TARIFFS = {
    "week": {"title": "Пропуск на неделю", "price": 25},   # 50 Stars
    "month": {"title": "Пропуск на месяц", "price": 50}, # 150 Stars
    "forever": {"title": "Пропуск навсегда", "price": 100} # 500 Stars
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- КЛАВИАТУРА С ТАРИФАМИ ---
def get_tariffs_kb():
    builder = InlineKeyboardBuilder()
    for key, data in TARIFFS.items():
        builder.button(text=f"{data['title']} — {data['price']} Stars", callback_data=f"buy_{key}")
    builder.adjust(1)
    return builder.as_markup()

# --- ХЭНДЛЕР /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Выберите тариф для покупки пропуска:",
        reply_markup=get_tariffs_kb()
    )

# --- ХЭНДЛЕР КНОПКИ ТАРИФА (ОТПРАВКА ИНВОЙСА) ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    tariff_key = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    # Отправляем инвойс на оплату в Stars
    # Для Stars: currency="XTR", provider_token="" (пустая строка)
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=tariff["title"],
        description=f"Покупка: {tariff['title']}",
        payload=f"tariff_{tariff_key}", # payload поможет идентифицировать тариф при успешной оплате
        provider_token="", # Пустая строка для Stars
        currency="XTR",    # Код валюты для Telegram Stars
        prices=[LabeledPrice(label=tariff["title"], amount=tariff["price"])],
        start_parameter=f"buy_{tariff_key}",
        # photo_url="URL_КАРТИНКИ", # Можно добавить картинку
    )
    await callback.answer()

# --- ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА ЗАКАЗА (ОБЯЗАТЕЛЬНО) ---
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    # Здесь можно проверить наличие товара, цены и т.д.
    # В данном случае просто подтверждаем.
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

# --- УСПЕШНАЯ ОПЛАТА (УВЕДОМЛЕНИЕ АДМИНА) ---
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payment = message.successful_payment
    user = message.from_user
    
    # Извлекаем тариф из payload
    tariff_key = payment.invoice_payload.replace("tariff_", "")
    tariff_data = TARIFFS.get(tariff_key, {"title": "Неизвестный тариф"})
    
    # 1. Сообщение пользователю
    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"Тариф: {tariff_data['title']}\n"
        f"Сумма: {payment.total_amount} Stars"
    )

    # 2. Уведомление админу
    admin_text = (
        f"💰 <b>Новая покупка!</b>\n\n"
        f"👤 Пользователь: {user.full_name}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"🔗 Username: @{user.username if user.username else 'нет'}\n\n"
        f"📦 Тариф: {tariff_data['title']}\n"
        f"⭐️ Сумма: {payment.total_amount} Stars\n"
        f"🧾 ID платежа: <code>{payment.telegram_payment_charge_id}</code>"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
