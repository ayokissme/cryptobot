from create_bot import bot, dp
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from coin_data.py import get_funding_rates
from aiogram.dispatcher.filters import Text
from keyboards import main_keyboard, cancel_keyboard
from aiogram.dispatcher.filters.state import State, StatesGroup


class FundingRatesForm(StatesGroup):
    coin = State()


async def command_start_rates(message: types.Message):
    await bot.send_message(message.chat.id, 'Enter the name of the currency in the format BTC, ETH, BNB, LTC', reply_markup=cancel_keyboard)
    await FundingRatesForm.coin.set()


async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await bot.send_message(message.chat.id, "Let's start from the beginning 😌", reply_markup=main_keyboard)


async def funding_rates(message: types.Message):
    value = await get_funding_rates(message.text.upper())
    if value == KeyError:
        await bot.send_message(message.chat.id, 'I have no information about this currency. Check if you entered the currency name correctly.')
    else:
        result = await create_text(message.text.upper(), value)
        text = result[0]
        inline_keyboard = result[1]
        await bot.send_message(message.chat.id, text, reply_markup=inline_keyboard)
    await FundingRatesForm.coin.set()


@dp.callback_query_handler(lambda callback: callback.data == 'refresh rate', state='*')
async def refresh_callback(callback: types.CallbackQuery):
    coin_symbol = callback.message.text.split('\n')[0].split(':')[0].upper()
    value = await get_funding_rates(coin_symbol)
    result = await create_text(coin_symbol, value)
    text = result[0]
    inline_keyboard = result[1]
    if text.strip() != callback.message.text.strip():
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=text,
            reply_markup=inline_keyboard
        )
        await callback.answer()
    else:
        await callback.answer('No changes')


async def create_text(message, value):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup_item = types.InlineKeyboardButton(text="Refresh 🔁", callback_data="refresh rate")
    markup.add(markup_item)
    text = f"{message}:\n"
    for rate in list(value):
        text += f"{value[rate]['emoji']} {rate}: {value[rate]['rate']}%\n"
    return text, markup


def register_funding_rates_handler(dispatcher: Dispatcher):
    dispatcher.register_message_handler(command_start_rates, Text(equals='Funding Rates 💸', ignore_case=True), state=None)
    dispatcher.register_message_handler(cancel_handler, Text(equals='❌ Cancel', ignore_case=True), state='*')
    dispatcher.register_message_handler(funding_rates, state=FundingRatesForm.coin)
