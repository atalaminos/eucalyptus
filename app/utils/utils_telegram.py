import asyncio

from telegram import Bot

from modules.helpers.conf import Conf

conf = Conf.get_conf()


class UtilsTelegram:

    @staticmethod
    def enviar_mensaje(texto: str):
        asyncio.run(UtilsTelegram._enviar_mensaje(texto))

    @staticmethod
    async def _enviar_mensaje(texto: str):
        bot = Bot(token=conf.get('TELEGRAM_TOKEN'))

        await bot.send_message(
            chat_id="137566456",
            text=texto
        )