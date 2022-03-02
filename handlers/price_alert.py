import asyncio
import json
from create_bot import bot, db
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from coin_data.py import get_ticker, get_coin_data
from notification import check_coins
from aiogram.dispatcher.filters.state import State, StatesGroup
from keyboards import main_keyboard, alert_keyboard, cancel_keyboard


class AlertForm(StatesGroup):
    coin_name = State()
    coin_price = State()


async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await bot.send_message(message.chat.id, "Let's start from the beginning 😌", reply_markup=main_keyboard)


async def select_alert(message: types.Message):
    await bot.send_message(message.chat.id, "Select:", reply_markup=alert_keyboard)


async def create_alert(message: types.message):
    await AlertForm.coin_name.set()
    await bot.send_message(message.chat.id, 'Type the name of the currency (BTC, ETH, BNB)', reply_markup=cancel_keyboard)


async def set_coin_name_invalid(message: types.Message):
    return await message.reply("No currency with this name was found 😕")


async def set_coin_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['coin_name'] = message.text.upper()
        data['coin_ticker'] = await get_ticker(message.text.upper())
    await AlertForm.next()
    await bot.send_message(message.chat.id, 'Enter the price at which the bot will notify you.'
                                            '\n\nIf the number is not an integer, then enter it separated by a dot. For example:\n\n- 0.2\n- 10.5\n- 8.40')


async def set_coin_price_invalid(message: types.Message):
    return await message.reply("The price was entered incorrectly 😕 Try again")


async def set_coin_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['coin_price'] = message.text
        data['last_price'] = (await get_coin_data(data['coin_ticker']))['quotes']['USD']['price']
        data['user_id'] = message.from_user.id
        await db.save_alert(data)
        await bot.send_message(message.chat.id, f"That's it! The bot will notify you when the {data['coin_name']} price reaches ${data['coin_price']}",
                               reply_markup=main_keyboard)
        tasks = [t.get_name() for t in asyncio.all_tasks()]
        if str(message.chat.id) not in tasks:
            user_id = message.chat.id
            asyncio.Task(check_coins(user_id)).set_name(user_id)
        print(len(asyncio.all_tasks()))
    await state.finish()


async def show_alerts(message: types.Message):
    alerts = await db.show_alerts(message.from_user.id)
    if alerts is None:
        await message.answer("No alert added")
    else:
        await message.answer(alerts)


def isfloat(message):
    try:
        float(message)
        return True
    except:
        return False


def register_alert_handler(dispatcher: Dispatcher):
    dispatcher.register_message_handler(cancel_handler, Text(equals='❌ Cancel', ignore_case=True), state='*')
    dispatcher.register_message_handler(select_alert, Text(equals='Price alert 📈', ignore_case=True))
    dispatcher.register_message_handler(create_alert, Text(equals='➕ Add alert', ignore_case=True))

    dispatcher.register_message_handler(set_coin_name_invalid,
                                        lambda message: message.text.upper() not in json.load(open('coin_data/templates/coin_names.json', 'r')).values(),
                                        state=AlertForm.coin_name)
    dispatcher.register_message_handler(set_coin_name, state=AlertForm.coin_name)

    dispatcher.register_message_handler(set_coin_price_invalid,
                                        lambda message: not isfloat(message.text),
                                        state=AlertForm.coin_price)
    dispatcher.register_message_handler(set_coin_price, state=AlertForm.coin_price)

    dispatcher.register_message_handler(show_alerts, Text(equals='🗂 Show alerts', ignore_case=True))
