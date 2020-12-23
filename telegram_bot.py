import os
import logging
import redis

from telegram_logger import TelegramLogsHandler
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from elasticpath import (
    fetch_products, get_product, get_image_url,
    add_to_cart, get_carts_products, get_total_price,
    remove_from_cart, create_customer,
)

_database = None
logger = logging.getLogger("dvmn_bot_telegram")


def start(bot, update):
    reply_markup = get_menu_keyboard_markup()
    update.message.reply_text('Выберите пиццу:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(bot, update):
    query = update.callback_query
    bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
    )
    if query.data == 'HANDLE_CART':
        keyboard = []
        cart_info = ''
        for item in get_carts_products(chat_id=query.message.chat_id):
            product_cart_id = item['id']
            name = item['name']
            description = item['description']
            item_info = item['meta']['display_price']['with_tax']
            price_per_unit = item_info['unit']['amount']
            price = item_info['value']['amount']
            quantity = int(float(price)/float(price_per_unit))
            cart_info += f"<b>{name}</b>\n{description}\nСтоимость: {price_per_unit}\n\nКоличество в корзине: {quantity} на сумму {price} руб\n\n"

            keyboard.append(
                [InlineKeyboardButton(
                    f'Убрать из корзины {name}', callback_data=product_cart_id
                )]
            )
        cart_info += f'<b>Всего:</b> {get_total_price(chat_id=query.message.chat_id)}'
        keyboard += [
            [InlineKeyboardButton('Оплатить', callback_data='WAITING_EMAIL')],
            [InlineKeyboardButton('В меню', callback_data='HANDLE_MENU')]
        ]
        bot.send_message(
            text=cart_info,
            chat_id=query.message.chat_id,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
        )
        return 'HANDLE_CART'

    product = get_product(product_id=query.data)
    price = product['price'][0]['amount']
    currency = product['price'][0]['currency']
    product_info = f"{product['name']}\n{product['description']}\nЦена {price} {currency}\n"
    image_url = get_image_url(
        id=product['relationships']['main_image']['data']['id']
    )
    choise_keyboard = [
        InlineKeyboardButton(
            f'+{quantity}', callback_data=f'{query.data} {quantity}'
        ) for quantity in [1, 5, 10]
    ]
    keyboard = [
        choise_keyboard,
        [InlineKeyboardButton('Назад', callback_data='HANDLE_MENU')],
    ]
    bot.send_photo(
        chat_id=query.message.chat_id,
        photo=image_url,
        caption=product_info,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return 'HANDLE_DESCRIPTION'


def handle_description(bot, update):
    query = update.callback_query
    if query.data == 'HANDLE_MENU':
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            text='Meню:',
            chat_id=query.message.chat_id,
            reply_markup=get_menu_keyboard_markup(),
        )
        return 'HANDLE_MENU'

    product_id, quantity = query.data.split(' ')
    add_to_cart(
        product_id=product_id,
        quantity=quantity,
        chat_id=query.message.chat_id
    )
    bot.answer_callback_query(
        callback_query_id=update.callback_query.id,
        text="Товар успешно добавлен в корзину!"
    )
    return 'HANDLE_DESCRIPTION'


def handle_cart(bot, update):
    query = update.callback_query
    if query.data == 'WAITING_EMAIL':
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            text='Введите ваш емайл:',
            chat_id=query.message.chat_id,
        )
        return 'WAITING_EMAIL'
    if query.data == 'HANDLE_MENU':
        bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
        bot.send_message(
            text='Meню:',
            chat_id=query.message.chat_id,
            reply_markup=get_menu_keyboard_markup(),
        )
        return 'HANDLE_MENU'

    remove_from_cart(product_id=query.data, chat_id=query.message.chat_id)
    return 'HANDLE_CART'


def waiting_email(bot, update):
    create_customer(
        name=update.message.chat.first_name,
        email=update.message.text,
    )
    bot.send_message(
            text='Ваш емайл добавлен в CRM',
            chat_id=update.message.chat_id,
        )
    return 'HANDLE_CART'


def get_menu_keyboard_markup():
    keyboard = [
        [InlineKeyboardButton(prod['name'], callback_data=prod['id'])] for prod in fetch_products()
    ]
    keyboard.append(
        [InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')]
    )
    return InlineKeyboardMarkup(keyboard)


def handle_users_reply(bot, update):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(bot, update)
    db.set(chat_id, next_state)


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.getenv("REDIS_PASSWORD")
        database_host = os.getenv("REDIS_HOST")
        database_port = os.getenv("REDIS_PORT")
        _database = redis.Redis(
            host=database_host, port=database_port, password=database_password
        )
    return _database


def error_handler(bot, update, err):
    logger.error(err)


if __name__ == '__main__':
    debug_bot_token = os.environ['DEBUG_TELEGRAM_BOT_TOKEN']
    debug_chat_id = os.environ['DEBUG_TELEGRAM_CHAT_ID']
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(
        debug_bot_token=debug_bot_token,
        chat_id=debug_chat_id,
    ))

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_handler)
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    logger.info('Бот Интернет-магазина в Telegram запущен')
    updater.start_polling()
