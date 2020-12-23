import logging
import telegram


class TelegramLogsHandler(logging.Handler):
    def __init__(self, debug_bot_token, chat_id):
        super().__init__()
        self.debug_bot = telegram.Bot(debug_bot_token)
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        self.debug_bot.send_message(self.chat_id, text=log_entry)
