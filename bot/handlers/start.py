"""
РћР±СЂР°Р±РѕС‚С‡РёРєРё РєРѕРјР°РЅРґ /start Рё РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ
"""

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder


router = Router()


def build_main_keyboard():
    """РЎРѕР·РґР°РµС‚ РіР»Р°РІРЅСѓСЋ РєР»Р°РІРёР°С‚СѓСЂСѓ РјРµРЅСЋ."""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="рџѓЏ РљР°СЂС‚С‹ РўР°СЂРѕ"))
    builder.row(types.KeyboardButton(text="рџ”ў РќСѓРјРµСЂРѕР»РѕРіРёСЏ"))
    builder.row(types.KeyboardButton(text="в™€пёЏ Р“РѕСЂРѕСЃРєРѕРї"))
    builder.row(types.KeyboardButton(text="рџЊЊ РђСЃС‚СЂРѕР»РѕРіРёСЏ"))
    builder.row(types.KeyboardButton(text="рџ§ РњРµРґРёС‚Р°С†РёСЏ"))
    builder.row(types.KeyboardButton(text="рџ’° Р¤РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ"))
    builder.row(types.KeyboardButton(text="рџЋІ РЎР»СѓС‡Р°Р№РЅРѕРµ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµ"))
    builder.row(types.KeyboardButton(text="рџ“– РЎРѕРЅРЅРёРє"), types.KeyboardButton(text="бљ± Р СѓРЅС‹"))
    builder.row(types.KeyboardButton(text="рџ” Р РµР¶РёРј РР"))
    builder.row(types.KeyboardButton(text="рџ”„ Р“РёР±СЂРёРґРЅС‹Р№ СЂРµР¶РёРј"))
    builder.row(types.KeyboardButton(text="рџ’Ћ РљРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ (777 в‚Ѕ)"))
    builder.row(types.KeyboardButton(text="рџ‘¤ РџСЂРѕС„РёР»СЊ"))
    return builder.as_markup(resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРѕРјР°РЅРґС‹ /start"""
    logging.info(f"Received /start from {message.from_user.id}")
    user = message.from_user

    welcome_text = f"""
вњЁ Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ, {user.first_name}!

РЇ вЂ” MysticBot, РІР°С€ РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹Р№ СЌР·РѕС‚РµСЂРёС‡РµСЃРєРёР№ РїРѕРјРѕС‰РЅРёРє.

рџѓЏ *РљР°СЂС‚С‹ РўР°СЂРѕ* вЂ” РїРѕР»СѓС‡Р°Р№С‚Рµ РјСѓРґСЂС‹Рµ СЃРѕРІРµС‚С‹ Рё РїСЂРµРґСЃРєР°Р·Р°РЅРёСЏ
рџ”ў *РќСѓРјРµСЂРѕР»РѕРіРёСЏ* вЂ” СЂР°СЃРєСЂРѕР№С‚Рµ С‚Р°Р№РЅС‹ С‡РёСЃРµР» РІР°С€РµР№ СЃСѓРґСЊР±С‹
в™€пёЏ *Р“РѕСЂРѕСЃРєРѕРїС‹* вЂ” РµР¶РµРґРЅРµРІРЅС‹Рµ, РЅРµРґРµР»СЊРЅС‹Рµ Рё РјРµСЃСЏС‡РЅС‹Рµ РїСЂРѕРіРЅРѕР·С‹
рџ’° *Р¤РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ* вЂ” Р°СЃС‚СЂРѕР»РѕРіРёС‡РµСЃРєРёРµ СЂРµРєРѕРјРµРЅРґР°С†РёРё РґР»СЏ С„РёРЅР°РЅСЃРѕРІ
рџ‘ђ *РҐРёСЂРѕРјР°РЅС‚РёСЏ* вЂ” Р°РЅР°Р»РёР· Р»РёРЅРёР№ РІР°С€РµР№ Р»Р°РґРѕРЅРё (СЃРєРѕСЂРѕ)
рџ“– *РЎРѕРЅРЅРёРє* вЂ” С‚РѕР»РєРѕРІР°РЅРёРµ СЃРЅРѕРІ
бљ± *Р СѓРЅС‹* вЂ” РґСЂРµРІРЅРµРµ РіР°РґР°РЅРёРµ

Р’С‹Р±РµСЂРёС‚Рµ РёРЅС‚РµСЂРµСЃСѓСЋС‰СѓСЋ РІР°СЃ С‚РµРјСѓ РёР· РјРµРЅСЋ РЅРёР¶Рµ!
"""

    keyboard = build_main_keyboard()

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРѕРјР°РЅРґС‹ /help вЂ” РїРѕРєР°Р·С‹РІР°РµС‚ РєСЂР°С‚РєСѓСЋ РёРЅСЃС‚СЂСѓРєС†РёСЋ Рё РјРµРЅСЋ"""
    help_text = """
рџ“– *РџРѕРјРѕС‰СЊ РїРѕ MysticBot*

РЇ СЂР°Р±РѕС‚Р°СЋ С‡РµСЂРµР· РєРЅРѕРїРєРё РјРµРЅСЋ вЂ” РїСЂРѕСЃС‚Рѕ РІС‹Р±РµСЂРёС‚Рµ РЅСѓР¶РЅС‹Р№ СЂР°Р·РґРµР» РЅРёР¶Рµ!

*РћСЃРЅРѕРІРЅС‹Рµ СЂР°Р·РґРµР»С‹:*
рџѓЏ РљР°СЂС‚С‹ РўР°СЂРѕ вЂ” СЂР°СЃРєР»Р°РґС‹ Рё РїСЂРµРґСЃРєР°Р·Р°РЅРёСЏ
рџ”ў РќСѓРјРµСЂРѕР»РѕРіРёСЏ вЂ” С‡РёСЃР»Р° СЃСѓРґСЊР±С‹
в™€пёЏ Р“РѕСЂРѕСЃРєРѕРї вЂ” РїСЂРѕРіРЅРѕР·С‹ РїРѕ Р·РЅР°РєР°Рј Р·РѕРґРёР°РєР°
рџЊЊ РђСЃС‚СЂРѕР»РѕРіРёСЏ вЂ” РЅР°С‚Р°Р»СЊРЅР°СЏ РєР°СЂС‚Р°, С‚СЂР°РЅР·РёС‚С‹, СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ
рџ§ РњРµРґРёС‚Р°С†РёСЏ вЂ” РїСЂР°РєС‚РёРєРё РґР»СЏ СѓРјР° Рё С‚РµР»Р°
рџ’° Р¤РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ вЂ” Р°СЃС‚СЂРѕР»РѕРіРёС‡РµСЃРєРёРµ СЂРµРєРѕРјРµРЅРґР°С†РёРё
рџ“– РЎРѕРЅРЅРёРє вЂ” С‚РѕР»РєРѕРІР°РЅРёРµ СЃРЅРѕРІ
бљ± Р СѓРЅС‹ вЂ” РґСЂРµРІРЅРµРµ РіР°РґР°РЅРёРµ
рџЋІ РЎР»СѓС‡Р°Р№РЅРѕРµ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµ вЂ” РјРіРЅРѕРІРµРЅРЅР°СЏ РјСѓРґСЂРѕСЃС‚СЊ
рџ” Р РµР¶РёРј РР вЂ” РІСЃРµ С‚РµРєСЃС‚РѕРІС‹Рµ СЃРѕРѕР±С‰РµРЅРёСЏ РѕР±СЂР°Р±Р°С‚С‹РІР°СЋС‚СЃСЏ РР
рџ”„ Р“РёР±СЂРёРґРЅС‹Р№ СЂРµР¶РёРј вЂ” С‡РµСЂРЅРѕРІРёРє РѕС‚РІРµС‚Р° СЃ РІРѕР·РјРѕР¶РЅРѕСЃС‚СЊСЋ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ
рџ’Ћ РљРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ (777 в‚Ѕ) вЂ” РїРµСЂСЃРѕРЅР°Р»СЊРЅР°СЏ СЂР°Р±РѕС‚Р° СЃ РјР°РіРѕРј
рџ‘¤ РџСЂРѕС„РёР»СЊ вЂ” РІР°С€Рё РЅР°СЃС‚СЂРѕР№РєРё Рё СЃС‚Р°С‚РёСЃС‚РёРєР°

*РљР°Рє РїРѕР»СЊР·РѕРІР°С‚СЊСЃСЏ:*
1. РќР°Р¶РјРёС‚Рµ РЅР° РєРЅРѕРїРєСѓ РЅСѓР¶РЅРѕРіРѕ СЂР°Р·РґРµР»Р°
2. РЎР»РµРґСѓР№С‚Рµ РїРѕРґСЃРєР°Р·РєР°Рј Р±РѕС‚Р°
3. РџРѕР»СѓС‡Р°Р№С‚Рµ РїРµСЂСЃРѕРЅР°Р»РёР·РёСЂРѕРІР°РЅРЅС‹Рµ СЂРµР·СѓР»СЊС‚Р°С‚С‹

Р’СЃС‘ РїСЂРѕСЃС‚Рѕ вЂ” РЅРёРєР°РєРёС… РєРѕРјР°РЅРґ Р·Р°РїРѕРјРёРЅР°С‚СЊ РЅРµ РЅСѓР¶РЅРѕ! вњЁ
"""
    # РџРѕРєР°Р·С‹РІР°РµРј С‚Рѕ Р¶Рµ РјРµРЅСЋ, С‡С‚Рѕ Рё РІ /start
    keyboard = build_main_keyboard()

    await message.answer(help_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """РРЅС„РѕСЂРјР°С†РёСЏ Рѕ РїСЂРµРјРёСѓРј-РїРѕРґРїРёСЃРєРµ"""
    premium_text = """
рџЊџ РџСЂРµРјРёСѓРј-РїРѕРґРїРёСЃРєР° MysticBot

Р§С‚Рѕ РІС…РѕРґРёС‚:
вњ… РќРµРѕРіСЂР°РЅРёС‡РµРЅРЅС‹Рµ СЂР°СЃРєР»Р°РґС‹ РўР°СЂРѕ
вњ… Р Р°СЃС€РёСЂРµРЅРЅС‹Рµ РЅСѓРјРµСЂРѕР»РѕРіРёС‡РµСЃРєРёРµ РѕС‚С‡С‘С‚С‹
вњ… РџРѕРґСЂРѕР±РЅС‹Рµ РіРѕСЂРѕСЃРєРѕРїС‹ РЅР° РјРµСЃСЏС†
вњ… РџРµСЂСЃРѕРЅР°Р»СЊРЅС‹Р№ С„РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ
вњ… РџСЂРёРѕСЂРёС‚РµС‚РЅР°СЏ РїРѕРґРґРµСЂР¶РєР°
вњ… РќРѕРІС‹Рµ С„СѓРЅРєС†РёРё РїРµСЂРІС‹РјРё

РЎС‚РѕРёРјРѕСЃС‚СЊ: 299 в‚Ѕ/РјРµСЃСЏС†

Р”Р»СЏ РѕС„РѕСЂРјР»РµРЅРёСЏ РїРѕРґРїРёСЃРєРё СЃРІСЏР¶РёС‚РµСЃСЊ СЃ @admin
"""
    await message.answer(premium_text, parse_mode="Markdown")


@router.message(Command("price"))
async def cmd_price(message: Message):
    """РРЅС„РѕСЂРјР°С†РёСЏ Рѕ РїРµСЂСЃРѕРЅР°Р»СЊРЅРѕР№ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёРё"""
    logging.info(f"Received /price from {message.from_user.id}")
    price_text = """
рџ’Ћ РџРµСЂСЃРѕРЅР°Р»СЊРЅР°СЏ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ РјР°РіР°

Р§С‚Рѕ РІС…РѕРґРёС‚:
вњ… Р“Р»СѓР±РѕРєРёР№ Р°РЅР°Р»РёР· РІР°С€РµР№ СЃРёС‚СѓР°С†РёРё
вњ… РџРѕРґР±РѕСЂ СЂР°СЃРєР»Р°РґР° РўР°СЂРѕ (5+ РєР°СЂС‚)
вњ… РќСѓРјРµСЂРѕР»РѕРіРёС‡РµСЃРєРёР№ РїРѕСЂС‚СЂРµС‚
вњ… РђСЃС‚СЂРѕР»РѕРіРёС‡РµСЃРєР°СЏ РєР°СЂС‚Р° РЅР° РјРµСЃСЏС†
вњ… РџРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ СЂРµРєРѕРјРµРЅРґР°С†РёРё
вњ… РћС‚РІРµС‚С‹ РЅР° 3 РІР°С€РёС… РІРѕРїСЂРѕСЃР°

РЎС‚РѕРёРјРѕСЃС‚СЊ: 777 в‚Ѕ (РµРґРёРЅРѕСЂР°Р·РѕРІРѕ)

РљР°Рє Р·Р°РєР°Р·Р°С‚СЊ:
1. РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ В«Р—Р°РєР°Р·Р°С‚СЊ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋВ» РЅРёР¶Рµ
2. РЈРєР°Р¶РёС‚Рµ РІР°С€ РІРѕРїСЂРѕСЃ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ
3. РћРїР»Р°С‚РёС‚Рµ 777 в‚Ѕ РЅР° РєР°СЂС‚Сѓ 2200 1234 5678 9012 (РўРёРЅСЊРєРѕС„С„)
4. РџРѕСЃР»Рµ РѕРїР»Р°С‚С‹ РѕС‚РїСЂР°РІСЊС‚Рµ СЃРєСЂРёРЅС€РѕС‚ С‡РµРєР° @Mystictestadminbot РґР»СЏ СЂСѓС‡РЅРѕР№ РїСЂРѕРІРµСЂРєРё
5. РџРѕР»СѓС‡РёС‚Рµ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ РІ С‚РµС‡РµРЅРёРµ 24 С‡Р°СЃРѕРІ РїРѕСЃР»Рµ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РѕРїР»Р°С‚С‹
"""
    # РЎРѕР·РґР°РµРј inline-РєР»Р°РІРёР°С‚СѓСЂСѓ СЃ РєРЅРѕРїРєРѕР№ Р·Р°РєР°Р·Р°
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="рџ›’ Р—Р°РєР°Р·Р°С‚СЊ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ", callback_data="order_consultation")
    keyboard = builder.as_markup()

    await message.answer(price_text, reply_markup=keyboard, parse_mode=None)


@router.message(F.text == "рџ’Ћ РљРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ (777 в‚Ѕ)")
async def handle_price_button(message: Message):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РєРѕРЅСЃСѓР»СЊС‚Р°С†РёРё"""
    await cmd_price(message)


# РћР±СЂР°Р±РѕС‚С‡РёРє РїРµСЂРµРЅРµСЃРµРЅ РІ orders.py

# РћР±СЂР°Р±РѕС‚С‡РёРєРё С‚РµРєСЃС‚РѕРІС‹С… РєРЅРѕРїРѕРє РіР»Р°РІРЅРѕРіРѕ РјРµРЅСЋ
@router.message(F.text == "рџѓЏ РљР°СЂС‚С‹ РўР°СЂРѕ")
async def handle_tarot_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РўР°СЂРѕ"""
    from bot.handlers.tarot import cmd_tarot
    await cmd_tarot(message, state)


@router.message(F.text == "рџ”ў РќСѓРјРµСЂРѕР»РѕРіРёСЏ")
async def handle_numerology_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РЅСѓРјРµСЂРѕР»РѕРіРёРё"""
    from bot.handlers.numerology import cmd_numerology
    await cmd_numerology(message, state)


@router.message(F.text == "в™€пёЏ Р“РѕСЂРѕСЃРєРѕРї")
async def handle_horoscope_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РіРѕСЂРѕСЃРєРѕРїР°"""
    from bot.handlers.horoscope import cmd_horoscope
    await cmd_horoscope(message)


@router.message(F.text == "рџ’° Р¤РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ")
async def handle_finance_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё С„РёРЅР°РЅСЃРѕРІРѕРіРѕ РєР°Р»РµРЅРґР°СЂСЏ"""
    from bot.handlers.finance_calendar import cmd_finance
    await cmd_finance(message)


@router.message(F.text == "рџЊЊ РђСЃС‚СЂРѕР»РѕРіРёСЏ")
async def handle_astrology_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё Р°СЃС‚СЂРѕР»РѕРіРёРё"""
    from bot.handlers.astrology import cmd_astrology
    await cmd_astrology(message, state)


@router.message(F.text == "рџ§ РњРµРґРёС‚Р°С†РёСЏ")
async def handle_meditation_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РјРµРґРёС‚Р°С†РёРё"""
    from bot.handlers.meditation import cmd_meditation
    await cmd_meditation(message, state)


@router.message(F.text == "рџ“– РЎРѕРЅРЅРёРє")
async def handle_dream_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё СЃРѕРЅРЅРёРєР°"""
    from bot.handlers.dream import cmd_dream
    await cmd_dream(message, state)


@router.message(F.text == "бљ± Р СѓРЅС‹")
async def handle_runes_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё СЂСѓРЅ"""
    from bot.handlers.runes import cmd_runes
    await cmd_runes(message, state)


@router.message(F.text == "рџЋІ РЎР»СѓС‡Р°Р№РЅРѕРµ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµ")
async def handle_random_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё СЃР»СѓС‡Р°Р№РЅРѕРіРѕ РїСЂРµРґСЃРєР°Р·Р°РЅРёСЏ"""
    from bot.handlers.random import cmd_random
    await cmd_random(message)


@router.message(F.text == "рџ¤– РљРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ AI")
async def handle_ask_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РєРѕРЅСЃСѓР»СЊС‚Р°С†РёРё AI"""
    from bot.handlers.ask import cmd_ask
    await cmd_ask(message, state)


@router.message(F.text == "рџ‘¤ РџСЂРѕС„РёР»СЊ")
async def handle_profile_button(message: Message):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РїСЂРѕС„РёР»СЏ"""
    from bot.handlers.profile import cmd_profile
    await cmd_profile(message)


@router.message(F.text == "рџ” Р РµР¶РёРј РР")
async def handle_ai_mode_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё СЂРµР¶РёРјР° РР"""
    from bot.handlers.ai_mode import handle_ai_mode_button as ai_mode_handler
    await ai_mode_handler(message, state)


@router.message(F.text == "рџ”„ Р“РёР±СЂРёРґРЅС‹Р№ СЂРµР¶РёРј")
async def handle_hybrid_mode_button(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РєРЅРѕРїРєРё РіРёР±СЂРёРґРЅРѕРіРѕ СЂРµР¶РёРјР°"""
    from bot.handlers.ai_mode import handle_hybrid_mode_button
    await handle_hybrid_mode_button(message, state)
