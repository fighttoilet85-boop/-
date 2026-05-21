import datetime
import sqlite3
import time
from telebot import TeleBot, types

# Твой рабочий токен от @BotFather
TOKEN = ""
bot = TeleBot(TOKEN)

# Настройка базы данных
def init_db():
    conn = sqlite3.connect("barista_game.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 100,
        stars_currency INTEGER DEFAULT 0,
        beans INTEGER DEFAULT 5,
        milk INTEGER DEFAULT 0,
        syrup INTEGER DEFAULT 0,
        cooking_finish_time TEXT DEFAULT NULL,
        cooking_coffee_type TEXT DEFAULT NULL
    )
    """)
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect("barista_game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def register_player(user_id):
    if get_player(user_id) is None:
        conn = sqlite3.connect("barista_game.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

def update_player(user_id, **kwargs):
    conn = sqlite3.connect("barista_game.db")
    cursor = conn.cursor()
    set_query = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    cursor.execute(f"UPDATE users SET {set_query} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

# НАСТРОЙКА ВРЕМЕНИ: Уровень 1 - 5с, Уровень 2 - 15с, Уровень 3 - 30с
RECIPES = {
    "Эспрессо": {"level": 1, "beans": 1, "milk": 0, "syrup": 0, "time": 5, "reward_coins": 20, "reward_exp": 10},
    "Капучино": {"level": 2, "beans": 1, "milk": 1, "syrup": 0, "time": 15, "reward_coins": 50, "reward_exp": 25},
    "Раф": {"level": 3, "beans": 1, "milk": 1, "syrup": 1, "time": 30, "reward_coins": 100, "reward_exp": 50}
}

SHOP_PRICES = {"beans": 10, "milk": 15, "syrup": 20}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("☕ Варить Кофе", "📦 Закупка")
    markup.row("👤 Моя Кофейня", "⭐ Донат (Stars)")
    return markup

@bot.message_handler(commands=['start'])
def start_game(message):
    register_player(message.from_user.id)
    bot.send_message(
        message.chat.id, 
        "☕ Симулятор Бариста запущен!\n\nИспользуй меню внизу для игры.", 
        reply_markup=main_keyboard()
    )

# Обработка секретной команды как обычной команды через слэш
@bot.message_handler(commands=['ZhopaPipa_PE'])
def secret_cheat_command(message):
    user_id = message.from_user.id
    register_player(user_id)
    
    # Начисляем горы ресурсов абсолютно бесплатно
    update_player(
        user_id, 
        coins=9999, 
        stars_currency=9999, 
        beans=999, 
        milk=999, 
        syrup=999,
        level=3 # Сразу даем 3 уровень, чтобы открылись все рецепты кофе!
    )
    bot.send_message(
        message.chat.id, 
        "🧙‍♂️ **Режим Создателя активирован!**\n\nТебе бесплатно начислено:\n💰 9999 монет\n🌟 9999 Золотых зёрен\n📦 По 999шт всех ингредиентов\n📈 Уровень повышен до 3!", 
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['text'])
def handle_menu(message):
    user_id = message.from_user.id
    register_player(user_id)
    p = get_player(user_id)
    
    level, exp, coins, stars_currency, beans, milk, syrup, cook_time, coffee_type = p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]

    if message.text == "👤 Моя Кофейня":
        status_text = (
            f"🏪 **Твоя кофейня**\n\n"
            f"⭐ Уровень: {level} (Опыт: {exp}/{(level*100)})\n"
            f"💰 Монеты: {coins}\n"
            f"🌟 Золотые зёрна: {stars_currency}\n\n"
            f"📦 **Склад:**\n"
            f"▫️ Зёрна: {beans} шт. | Молоко: {milk} шт. | Сироп: {syrup} шт."
        )
        bot.send_message(message.chat.id, status_text, parse_mode="Markdown")

    elif message.text == "📦 Закупка":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"Зёрна ({SHOP_PRICES['beans']} мон.)", callback_data="buy_beans"))
        markup.add(types.InlineKeyboardButton(f"Молоко ({SHOP_PRICES['milk']} мон.)", callback_data="buy_milk"))
        markup.add(types.InlineKeyboardButton(f"Сироп ({SHOP_PRICES['syrup']} мон.)", callback_data="buy_syrup"))
        bot.send_message(message.chat.id, "Что желаешь заказать для склада?", reply_markup=markup)

    elif message.text == "☕ Варить Кофе":
        if cook_time:
            finish = datetime.datetime.fromisoformat(cook_time)
            now = datetime.datetime.now()
            if now < finish:
                remaining = int((finish - now).total_seconds())
                bot.send_message(message.chat.id, f"⏳ Кофе готовится! Осталось {remaining} сек.")
                return
            else:
                recipe = RECIPES[coffee_type]
                new_coins = coins + recipe["reward_coins"]
                new_exp = exp + recipe["reward_exp"]
                
                new_level = level
                if new_exp >= (level * 100):
                    new_exp -= (level * 100)
                    new_level += 1
                    bot.send_message(message.chat.id, f"🎉 Уровень повышен до {new_level}!")

                update_player(user_id, coins=new_coins, exp=new_exp, level=new_level, cooking_finish_time=None, cooking_coffee_type=None)
                bot.send_message(message.chat.id, f"✅ Готово! Ты получил {recipe['reward_coins']} монет и {recipe['reward_exp']} опыта.")
                return

        markup = types.InlineKeyboardMarkup()
        for name, data in RECIPES.items():
            if level >= data["level"]:
                markup.add(types.InlineKeyboardButton(f"Сварить {name} ({data['time']} сек)", callback_data=f"cook_{name}"))
            else:
                markup.add(types.InlineKeyboardButton(f"🔒 {name} ({data['level']} ур.)", callback_data="locked"))
        bot.send_message(message.chat.id, "Выбери рецепт:", reply_markup=markup)

    elif message.text == "⭐ Донат (Stars)":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✨ 250 Золотых зёрен (5 Stars)", callback_data="pay_stars_250"))
        markup.add(types.InlineKeyboardButton("🔥 500 Золотых зёрен [Выгода!] (8 Stars)", callback_data="pay_stars_500"))
        markup.add(types.InlineKeyboardButton("📦 100 всех Ингредиентов (15 Stars)", callback_data="pay_stars_items"))
        markup.add(types.InlineKeyboardButton("📈 Буст Прокачки (+150 EXP) (10 Stars)", callback_data="pay_stars_exp"))
        
        bot.send_message(
            message.chat.id, 
            f"🌟 **Премиум-магазин Telegram Stars**\nУ тебя: {stars_currency} Золотых зёрен.\n\nВыбери товар:", 
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    p = get_player(user_id)
    if not p: return
        
    level, exp, coins, stars_currency, beans, milk, syrup, cook_time, coffee_type = p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]

    if call.data.startswith("buy_"):
        item = call.data.replace("buy_", "")
        price = SHOP_PRICES[item]
        if coins >= price:
            new_coins = coins - price
            if item == "beans": update_player(user_id, coins=new_coins, beans=beans+1)
            elif item == "milk": update_player(user_id, coins=new_coins, milk=milk+1)
            elif item == "syrup": update_player(user_id, coins=new_coins, syrup=syrup+1)
            bot.answer_callback_query(call.id, "Куплено!")
        else:
            bot.answer_callback_query(call.id, "Не хватает монет!", show_alert=True)

    elif call.data.startswith("cook_"):
        name = call.data.replace("cook_", "")
        recipe = RECIPES[name]
        if beans < recipe["beans"] or milk < recipe["milk"] or syrup < recipe["syrup"]:
            bot.answer_callback_query(call.id, "Не хватает ингредиентов на складе!", show_alert=True)
            return
            
        finish_time = (datetime.datetime.now() + datetime.datetime.timedelta(seconds=recipe["time"])).isoformat()
        update_player(user_id, beans=beans-recipe["beans"], milk=milk-recipe["milk"], syrup=syrup-recipe["syrup"], cooking_finish_time=finish_time, cooking_coffee_type=name)
        bot.edit_message_text(f"⏳ Варка {name} запущена на {recipe['time']} сек!", call.message.chat.id, call.message.message_id)

    elif call.data.startswith("pay_stars_"):
        action = call.data.replace("pay_stars_", "")
        
        if action == "250":
            title, desc, payload, amount = "250 Золотых зёрен", "Пакет валюты", "pack_250_beans", 5
        elif action == "500":
            title, desc, payload, amount = "500 Золотых зёрен", "Большой пакет валюты", "pack_500_beans", 8
        elif action == "items":
            title, desc, payload, amount = "100 Ингредиентов", "По 100шт всего на склад", "pack_100_items", 15
        elif action == "exp":
            title, desc, payload, amount = "Буст Прокачки", "Получение 150 опыта", "pack_boost_exp", 10
            
        prices = [types.LabeledPrice(label=title, amount=amount)]
        bot.send_invoice(
            call.message.chat.id, title=title, description=desc,
            provider_token="", currency="XTR", prices=prices, invoice_payload=payload
        )
        bot.answer_callback_query(call.id)

    elif call.data == "locked":
        bot.answer_callback_query(call.id, "Маловат уровень!", show_alert=True)

# --- ПРИЕМ ОПЛАТЫ ---
@bot.shipping_query_handler(func=lambda query: True)
def shipping(shipping_query):
    bot.answer_shipping_query(shipping_query.id, ok=True)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    p = get_player(user_id)
    if not p: return
    
    level, exp, coins, stars_currency, beans, milk, syrup = p[1], p[2], p[3], p[4], p[5], p[6], p[7]

    if payload == "pack_250_beans":
        update_player(user_id, stars_currency=stars_currency + 250)
        bot.send_message(message.chat.id, "🎉 Успешно! Тебе начислено 250 Золотых зёрен.")
    elif payload == "pack_500_beans":
        update_player(user_id, stars_currency=stars_currency + 500)
        bot.send_message(message.chat.id, "🎉 Успешно! Тебе начислено 500 Золотых зёрен.")
    elif payload == "pack_100_items":
        update_player(user_id, beans=beans + 100, milk=milk + 100, syrup=syrup + 100)
        bot.send_message(message.chat.id, "🎉 На склад доставлено по 100 шт. всех ингредиентов!")
    elif payload == "pack_boost_exp":
        new_exp = exp + 150
        new_level = level
        while new_exp >= (new_level * 100):
            new_exp -= (new_level * 100)
            new_level += 1
            bot.send_message(message.chat.id, f"🎉 Уровень повышен! Новый уровень: {new_level}")
        update_player(user_id, exp=new_exp, level=new_level)
        bot.send_message(message.chat.id, "🎉 Буст активирован! Опыт добавлен.")

if __name__ == "__main__":
    init_db()
    print("Бот успешно перезапущен с чит-командой!")
    bot.infinity_polling()
