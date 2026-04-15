import asyncio
import logging

from bot.bot import bot, dp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
