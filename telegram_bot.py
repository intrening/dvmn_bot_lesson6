import os
import logging
import redis
import requests

from telegram_logger import TelegramLogsHandler
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from validate_email import validate_email

from elasticpath import (
    fetch_products, get_product, get_image_url,
    add_to_cart, get_carts_products, get_total_price,
    remove_from_cart, create_customer,
)

_database = None
logger = logging.getLogger("dvmn_bot_telegram")

PRODUCTS_ON_PAGE = 8


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

    if 'page' in query.data:
        page = int(query.data.split(' ')[-1])
        bot.send_message(
            text='Meню:',
            chat_id=query.message.chat_id,
            reply_markup=get_menu_keyboard_markup(page=page),
        )
        return 'HANDLE_MENU'

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
    email = update.message.text
    if not validate_email(email):
        bot.send_message(
            text='Введите корректный емайл',
            chat_id=update.message.chat_id,
        )
        return 'WAITING_EMAIL'
    create_customer(
        name=update.message.chat.first_name,
        email=email,
    )
    bot.send_message(
            text='Ваш емайл добавлен в CRM, напишите ваш адрес текстом или отправьте геолокацию',
            chat_id=update.message.chat_id,
        )
    return 'HANDLE_WAITING_ADRESS'


def get_menu_keyboard_markup(page=1):
    products = fetch_products()
    first_product_num = (page-1)*PRODUCTS_ON_PAGE
    navigation_list = [] if page == 1 else [InlineKeyboardButton('<<<', callback_data=f'page {page-1}')]
    if page*PRODUCTS_ON_PAGE < len(products):
        last_product_num = page*PRODUCTS_ON_PAGE
        navigation_list.append(InlineKeyboardButton('>>>', callback_data=f'page {page+1}'))
    else:
        last_product_num = len(products)
    keyboard = [
        [InlineKeyboardButton(prod['name'], callback_data=prod['id'])] for prod in products[first_product_num:last_product_num]
    ]
    keyboard.append(navigation_list)
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='HANDLE_CART')])
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
        'HANDLE_WAITING_ADRESS': handle_waiting_adress,
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


def handle_waiting_adress(bot, update):
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    if message.location:
        current_pos = (message.location.latitude, message.location.longitude)
    current_pos = (fetch_coordinates(apikey=os.getenv('YANDEX_GEO_API'), place=update.message.text))


def fetch_coordinates(apikey, place):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {"geocode": place, "apikey": apikey, "format": "json"}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    places_found = response.json()['response']['GeoObjectCollection']['featureMember']
    most_relevant = places_found[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


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
    dispatcher.add_handler(MessageHandler(Filters.location, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    logger.info('Бот Интернет-магазина в Telegram запущен')
    updater.start_polling()
