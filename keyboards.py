from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData
import config


cbd = CallbackData('buy', 'id', 'name', 'price')

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text='Кнопка 1'), KeyboardButton(text='Кнопка 2')
        ],
        [
            KeyboardButton(text='Кнопка 3')
        ]
    ], resize_keyboard=True
)

keyboard1 = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='POCO', callback_data='buy:0:poco:19999'),
            InlineKeyboardButton(
                text='SAMSUNG', callback_data='buy:1:samsung:47499')
        ],
        [
            InlineKeyboardButton(text='Отмена', callback_data='cancel')
        ]
    ]
)

poco_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton('Купить', url=config.URL_GOODS1)
        ]
    ]
)

samsung_key = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton('Купить', url=config.URL_GOODS2)
        ]
    ]
)
