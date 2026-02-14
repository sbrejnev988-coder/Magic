"""
РђРґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅС‹Рµ РєРѕРјР°РЅРґС‹
"""

import logging

from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.order import OrderService, OrderStatus
from bot.services.hybrid_draft import HybridDraftService
from bot.database.engine import get_session_maker
from bot.config import Settings

log = logging.getLogger(__name__)

router = Router()
settings = Settings()


def is_admin(user_id: int) -> bool:
    """РџСЂРѕРІРµСЂРєР° РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
    return user_id == settings.ADMIN_USER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """РњРµРЅСЋ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
    if not is_admin(message.from_user.id):
        await message.answer("в›”пёЏ РЈ РІР°СЃ РЅРµС‚ РїСЂР°РІ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°.")
        return
    
    admin_text = """
вљ™пёЏ *РџР°РЅРµР»СЊ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°*

*РљРѕРјР°РЅРґС‹:*
/admin_stats вЂ” СЃС‚Р°С‚РёСЃС‚РёРєР° Р±РѕС‚Р°
/admin_broadcast вЂ” СЂР°СЃСЃС‹Р»РєР° СЃРѕРѕР±С‰РµРЅРёР№
/admin_users вЂ” СѓРїСЂР°РІР»РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё
/admin_db вЂ” СѓРїСЂР°РІР»РµРЅРёРµ Р±Р°Р·РѕР№ РґР°РЅРЅС‹С…
/admin_orders вЂ” СѓРїСЂР°РІР»РµРЅРёРµ Р·Р°РєР°Р·Р°РјРё

*Р‘С‹СЃС‚СЂС‹Рµ РґРµР№СЃС‚РІРёСЏ:*
- РџСЂРѕРІРµСЂРёС‚СЊ СЃРѕСЃС‚РѕСЏРЅРёРµ Р‘Р”
- РџРѕСЃРјРѕС‚СЂРµС‚СЊ Р»РѕРіРё
- Р”РѕР±Р°РІРёС‚СЊ РєРѕРЅС‚РµРЅС‚
"""
    await message.answer(admin_text, parse_mode="Markdown")


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    """РЎС‚Р°С‚РёСЃС‚РёРєР° РґР»СЏ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°"""
    if not is_admin(message.from_user.id):
        await message.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.")
        return
    
    stats_text = """
рџ“€ *РђРґРјРёРЅРёСЃС‚СЂР°С‚РёРІРЅР°СЏ СЃС‚Р°С‚РёСЃС‚РёРєР°*

*РџРѕР»СЊР·РѕРІР°С‚РµР»Рё:*
- Р’СЃРµРіРѕ: 1
- РќРѕРІС‹Рµ Р·Р° РґРµРЅСЊ: 1
- РђРєС‚РёРІРЅС‹Рµ Р·Р° РЅРµРґРµР»СЋ: 1

*Р—Р°РїСЂРѕСЃС‹:*
- Р’СЃРµРіРѕ: 0
- РЈСЃРїРµС€РЅС‹С…: 0
- РћС€РёР±РѕРє: 0

*РЎРёСЃС‚РµРјР°:*
- Р’СЂРµРјСЏ СЂР°Р±РѕС‚С‹: 0 С‡ 0 РјРёРЅ
- РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ РїР°РјСЏС‚Рё: ~50 MB
- Р‘Р°Р·Р° РґР°РЅРЅС‹С…: СЂР°Р±РѕС‚Р°РµС‚
"""
    await message.answer(stats_text, parse_mode="Markdown")


@router.message(Command("admin_broadcast"))
async def cmd_admin_broadcast(message: Message, command: CommandObject, state: FSMContext):
    """РќР°С‡Р°С‚СЊ СЂР°СЃСЃС‹Р»РєСѓ"""
    if not is_admin(message.from_user.id):
        await message.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.")
        return
    
    if not command.args:
        await message.answer("рџ“ў *Р Р°СЃСЃС‹Р»РєР°*\n\nРСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ: `/admin_broadcast С‚РµРєСЃС‚`", parse_mode="Markdown")
        return
    
    # Р—Р°РіР»СѓС€РєР°: РїСЂРѕСЃС‚Рѕ СЌС…Рѕ
    await message.answer(f"рџ“ў Р Р°СЃСЃС‹Р»РєР° (Р·Р°РіР»СѓС€РєР°):\n\n{command.args}")


@router.message(Command("admin_orders"))
async def cmd_admin_orders(message: Message, session_maker=None):
    """РЈРїСЂР°РІР»РµРЅРёРµ Р·Р°РєР°Р·Р°РјРё"""
    if not is_admin(message.from_user.id):
        await message.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.")
        return
    
    if session_maker is None:
        # Fallback РґР»СЏ РѕР±СЂР°С‚РЅРѕР№ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚Рё
        from bot.database.engine import get_session_maker
        from bot.config import Settings
        settings = Settings()
        from bot.database.engine import create_engine
        engine = create_engine(settings.DATABASE_URL)
        session_maker = get_session_maker(engine)
    
    async with session_maker() as session:
        order_service = OrderService(session)
        
        # РџРѕР»СѓС‡Р°РµРј РЅРµРѕРїР»Р°С‡РµРЅРЅС‹Рµ Р·Р°РєР°Р·С‹
        unpaid_orders = await order_service.get_unpaid_orders(limit=20)
        
        if not unpaid_orders:
            await message.answer("вњ… *РќРµС‚ РЅРµРѕРїР»Р°С‡РµРЅРЅС‹С… Р·Р°РєР°Р·РѕРІ.*", parse_mode="Markdown")
            return
        
        # РџРѕРєР°Р·С‹РІР°РµРј СЃРїРёСЃРѕРє Р·Р°РєР°Р·РѕРІ
        response = "рџ“‹ *РќРµРѕРїР»Р°С‡РµРЅРЅС‹Рµ Р·Р°РєР°Р·С‹:*\n\n"
        for order in unpaid_orders:
            response += f"рџ†” *Р—Р°РєР°Р· #{order.id}*\n"
            response += f"рџ‘¤ РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {order.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'} (@{order.username or 'РЅРµС‚'})\n"
            response += f"рџ“… Р”Р°С‚Р° СЂРѕР¶РґРµРЅРёСЏ: {order.birth_date}\n"
            response += f"вќ“ Р’РѕРїСЂРѕСЃ: {order.question[:100]}...\n"
            response += f"рџ•’ РЎРѕР·РґР°РЅ: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += f"рџ’і РћРїР»Р°С‡РµРЅ: {'вњ…' if order.is_paid else 'вќЊ'}\n"
            response += f"рџ“ё РЎРєСЂРёРЅС€РѕС‚: {'Р•СЃС‚СЊ' if order.payment_screenshot else 'РќРµС‚'}\n"
            response += "вЂ”" * 30 + "\n"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Р”Р»СЏ РєР°Р¶РґРѕРіРѕ Р·Р°РєР°Р·Р° СЃРѕР·РґР°РµРј inline-РєРЅРѕРїРєРё
        for order in unpaid_orders:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="вњ… РџРѕРґС‚РІРµСЂРґРёС‚СЊ РѕРїР»Р°С‚Сѓ", callback_data=f"confirm_payment:{order.id}"),
                types.InlineKeyboardButton(text="рџ“ќ Р—Р°РјРµС‚РєР°", callback_data=f"add_note:{order.id}")
            )
            # Р’С‚РѕСЂР°СЏ СЃС‚СЂРѕРєР°: РїРѕРґСЂРѕР±РЅРѕСЃС‚Рё Рё СЃРєСЂРёРЅС€РѕС‚ (РµСЃР»Рё РµСЃС‚СЊ)
            buttons_row2 = []
            buttons_row2.append(types.InlineKeyboardButton(text="рџ‘Ђ РџРѕРґСЂРѕР±РЅРµРµ", callback_data=f"order_details:{order.id}"))
            if order.payment_screenshot:
                buttons_row2.append(types.InlineKeyboardButton(text="рџ‘ЃпёЏ Р Р°СЃРє.СЃРєСЂРёРЅС€РѕС‚", callback_data=f"ocr_screenshot:{order.id}"))
            builder.row(*buttons_row2)
            
            order_text = (
                f"рџ†” *Р—Р°РєР°Р· #{order.id}*\n"
                f"рџ‘¤ РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {order.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'} (@{order.username or 'РЅРµС‚'})\n"
                f"вќ“ Р’РѕРїСЂРѕСЃ: {order.question[:200]}..."
            )
            await message.answer(order_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("confirm_payment:"))
async def handle_confirm_payment(callback: CallbackQuery, session_maker=None):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РѕРїР»Р°С‚С‹"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    if session_maker is None:
        # Fallback РґР»СЏ РѕР±СЂР°С‚РЅРѕР№ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚Рё
        from bot.database.engine import get_session_maker
        from bot.config import Settings
        settings = Settings()
        from bot.database.engine import create_engine
        engine = create_engine(settings.DATABASE_URL)
        session_maker = get_session_maker(engine)
    
    async with session_maker() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("вќЊ Р—Р°РєР°Р· РЅРµ РЅР°Р№РґРµРЅ.", show_alert=True)
            return
        
        # РџРѕРјРµС‡Р°РµРј РєР°Рє РѕРїР»Р°С‡РµРЅРЅС‹Р№
        updated_order = await order_service.mark_as_paid(order_id)
        
        if updated_order and updated_order.is_paid:
            await callback.answer("вњ… Р—Р°РєР°Р· РїРѕРјРµС‡РµРЅ РєР°Рє РѕРїР»Р°С‡РµРЅРЅС‹Р№.")
            
            # РћР±РЅРѕРІР»СЏРµРј СЃРѕРѕР±С‰РµРЅРёРµ
            await callback.message.edit_text(
                f"вњ… *Р—Р°РєР°Р· #{order_id} РѕРїР»Р°С‡РµРЅ*\n\n"
                f"РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {order.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'} (@{order.username or 'РЅРµС‚'})\n"
                f"Р’РѕРїСЂРѕСЃ: {order.question[:200]}...\n\n"
                f"РЎС‚Р°С‚СѓСЃ: РћРџР›РђР§Р•РќРћ",
                parse_mode="Markdown"
            )
        else:
            await callback.answer("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РѕР±РЅРѕРІРёС‚СЊ Р·Р°РєР°Р·.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("add_note:"))
async def handle_add_note(callback: CallbackQuery, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РґРѕР±Р°РІР»РµРЅРёСЏ Р·Р°РјРµС‚РєРё Рє Р·Р°РєР°Р·Сѓ"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    # РЎРѕС…СЂР°РЅСЏРµРј order_id РІ СЃРѕСЃС‚РѕСЏРЅРёРё Рё РїСЂРѕСЃРёРј РїСЂРёСЃР»Р°С‚СЊ С‚РµРєСЃС‚ Р·Р°РјРµС‚РєРё
    await state.update_data(admin_note_order_id=order_id)
    await callback.answer()
    
    await callback.message.answer(
        f"рџ“ќ *Р”РѕР±Р°РІР»РµРЅРёРµ Р·Р°РјРµС‚РєРё Рє Р·Р°РєР°Р·Сѓ #{order_id}*\n\n"
        "РћС‚РїСЂР°РІСЊС‚Рµ С‚РµРєСЃС‚ Р·Р°РјРµС‚РєРё. РћРЅР° Р±СѓРґРµС‚ СЃРѕС…СЂР°РЅРµРЅР° РІ РёРЅС„РѕСЂРјР°С†РёРё Рѕ Р·Р°РєР°Р·Рµ.",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_note(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє С‚РµРєСЃС‚РѕРІС‹С… СЃРѕРѕР±С‰РµРЅРёР№ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° РґР»СЏ РґРѕР±Р°РІР»РµРЅРёСЏ Р·Р°РјРµС‚РєРё"""
    data = await state.get_data()
    order_id = data.get("admin_note_order_id")
    
    if order_id:
        note_text = message.text.strip()
        if note_text:
            async with get_session_maker()() as session:
                order_service = OrderService(session)
                await order_service.add_admin_notes(order_id, note_text)
                
            await message.answer(f"вњ… Р—Р°РјРµС‚РєР° РґРѕР±Р°РІР»РµРЅР° Рє Р·Р°РєР°Р·Сѓ #{order_id}.")
            await state.clear()
        else:
            await message.answer("вќЊ РўРµРєСЃС‚ Р·Р°РјРµС‚РєРё РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")


@router.callback_query(lambda c: c.data.startswith("order_details:"))
async def handle_order_details(callback: CallbackQuery):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РїСЂРѕСЃРјРѕС‚СЂР° РґРµС‚Р°Р»РµР№ Р·Р°РєР°Р·Р°"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("вќЊ Р—Р°РєР°Р· РЅРµ РЅР°Р№РґРµРЅ.", show_alert=True)
            return
        
        details = (
            f"рџ“‹ *Р”РµС‚Р°Р»Рё Р·Р°РєР°Р·Р° #{order.id}*\n\n"
            f"рџ‘¤ *РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ:*\n"
            f"вЂў ID: {order.user_id}\n"
            f"вЂў РРјСЏ: {order.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'}\n"
            f"вЂў Username: @{order.username or 'РЅРµС‚'}\n\n"
            f"рџ“… *Р”Р°С‚Р° СЂРѕР¶РґРµРЅРёСЏ:* {order.birth_date}\n\n"
            f"вќ“ *Р’РѕРїСЂРѕСЃ:*\n{order.question}\n\n"
            f"рџ“Љ *РЎС‚Р°С‚СѓСЃ:* {order.status.value}\n"
            f"рџ’і *РћРїР»Р°С‡РµРЅ:* {'вњ… Р”Р°' if order.is_paid else 'вќЊ РќРµС‚'}\n"
            f"рџ“ё *РЎРєСЂРёРЅС€РѕС‚:* {'Р•СЃС‚СЊ' if order.payment_screenshot else 'РќРµС‚'}\n\n"
            f"рџ“ќ *Р—Р°РјРµС‚РєРё Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°:*\n{order.admin_notes or 'РќРµС‚'}\n\n"
            f"рџ•’ *РЎРѕР·РґР°РЅ:* {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"вњЏпёЏ *РћР±РЅРѕРІР»С‘РЅ:* {order.updated_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.answer()
        await callback.message.answer(details, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("ocr_screenshot:"))
async def handle_ocr_screenshot(callback: CallbackQuery):
    """Р Р°СЃРїРѕР·РЅР°РІР°РЅРёРµ С‚РµРєСЃС‚Р° РЅР° СЃРєСЂРёРЅС€РѕС‚Рµ РѕРїР»Р°С‚С‹"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("вќЊ Р—Р°РєР°Р· РЅРµ РЅР°Р№РґРµРЅ.", show_alert=True)
            return
        
        if not order.payment_screenshot:
            await callback.answer("вќЊ РЈ СЌС‚РѕРіРѕ Р·Р°РєР°Р·Р° РЅРµС‚ СЃРєСЂРёРЅС€РѕС‚Р°.", show_alert=True)
            return
        
        # РРЅС„РѕСЂРјРёСЂСѓРµРј Рѕ РЅР°С‡Р°Р»Рµ РѕР±СЂР°Р±РѕС‚РєРё
        await callback.answer("рџ”Ќ РќР°С‡РёРЅР°СЋ СЂР°СЃРїРѕР·РЅР°РІР°РЅРёРµ С‚РµРєСЃС‚Р°...")
        
        try:
            # РџС‹С‚Р°РµРјСЃСЏ РёРјРїРѕСЂС‚РёСЂРѕРІР°С‚СЊ EasyOCR
            import easyocr
            import tempfile
            import os
            from io import BytesIO
            
            # РЎРєР°С‡РёРІР°РµРј С„Р°Р№Р» РёР· Telegram
            # payment_screenshot РјРѕР¶РµС‚ Р±С‹С‚СЊ file_id
            file_id = order.payment_screenshot
            # РџРѕР»СѓС‡Р°РµРј РѕР±СЉРµРєС‚ С„Р°Р№Р»Р°
            file = await callback.bot.get_file(file_id)
            # РЎРєР°С‡РёРІР°РµРј С„Р°Р№Р» РІРѕ РІСЂРµРјРµРЅРЅС‹Р№ С„Р°Р№Р»
            file_bytes = await callback.bot.download_file(file.file_path)
            
            # РЎРѕС…СЂР°РЅСЏРµРј РІРѕ РІСЂРµРјРµРЅРЅС‹Р№ С„Р°Р№Р»
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(file_bytes.read())
                tmp_path = tmp.name
            
            try:
                # РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј С‡РёС‚Р°С‚РµР»СЊ (СЂСѓСЃСЃРєРёР№ + Р°РЅРіР»РёР№СЃРєРёР№)
                reader = easyocr.Reader(['en', 'ru'], gpu=False)
                # Р Р°СЃРїРѕР·РЅР°С‘Рј С‚РµРєСЃС‚
                results = reader.readtext(tmp_path, detail=0, paragraph=True)
                
                # Р¤РѕСЂРјРёСЂСѓРµРј СЂРµР·СѓР»СЊС‚Р°С‚
                if results:
                    extracted_text = "\n".join(results)
                    # РС‰РµРј РєР»СЋС‡РµРІС‹Рµ СЃР»РѕРІР°
                    keywords = ['РїРµСЂРµРІРѕРґ', 'РѕРїР»Р°С‚Р°', 'С‡РµРє', 'РїР»Р°С‚РµР¶', 'СЃСѓРјРјР°', 'СЂСѓР±', 'в‚Ѕ', '777']
                    found_keywords = [kw for kw in keywords if kw.lower() in extracted_text.lower()]
                    
                    result_message = (
                        f"рџ‘ЃпёЏ *Р Р°СЃРїРѕР·РЅР°РЅРЅС‹Р№ С‚РµРєСЃС‚ СЃ СЃРєСЂРёРЅС€РѕС‚Р° Р·Р°РєР°Р·Р° #{order.id}*\n\n"
                        f"рџ“„ *РР·РІР»РµС‡С‘РЅРЅС‹Р№ С‚РµРєСЃС‚:*\n```\n{extracted_text[:1500]}"
                    )
                    if len(extracted_text) > 1500:
                        result_message += "\n... (С‚РµРєСЃС‚ РѕР±СЂРµР·Р°РЅ)"
                    result_message += "\n```\n\n"
                    
                    if found_keywords:
                        result_message += f"вњ… *РќР°Р№РґРµРЅС‹ РєР»СЋС‡РµРІС‹Рµ СЃР»РѕРІР°:* {', '.join(found_keywords)}\n"
                    else:
                        result_message += "вљ пёЏ *РљР»СЋС‡РµРІС‹Рµ СЃР»РѕРІР° РЅРµ РЅР°Р№РґРµРЅС‹*\n"
                    
                    result_message += f"\n*РЎРѕРІРµС‚:* РџСЂРѕРІРµСЂСЊС‚Рµ РЅР°Р»РёС‡РёРµ СЃСѓРјРјС‹ 777 в‚Ѕ Рё СЂРµРєРІРёР·РёС‚РѕРІ."
                else:
                    result_message = f"вќЊ *РќРµ СѓРґР°Р»РѕСЃСЊ СЂР°СЃРїРѕР·РЅР°С‚СЊ С‚РµРєСЃС‚ РЅР° СЃРєСЂРёРЅС€РѕС‚Рµ Р·Р°РєР°Р·Р° #{order.id}*"
                
                await callback.message.answer(result_message, parse_mode="Markdown")
                
            except Exception as e:
                await callback.message.answer(
                    f"вќЊ *РћС€РёР±РєР° РїСЂРё СЂР°СЃРїРѕР·РЅР°РІР°РЅРёРё С‚РµРєСЃС‚Р°:*\n```{str(e)[:500]}```",
                    parse_mode="Markdown"
                )
            finally:
                # РЈРґР°Р»СЏРµРј РІСЂРµРјРµРЅРЅС‹Р№ С„Р°Р№Р»
                os.unlink(tmp_path)
                
        except ImportError:
            # EasyOCR РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ
            await callback.message.answer(
                f"рџ“ё *РЎРєСЂРёРЅС€РѕС‚ Р·Р°РєР°Р·Р° #{order.id}*\n\n"
                f"Р¤СѓРЅРєС†РёСЏ OCR РЅРµРґРѕСЃС‚СѓРїРЅР°. РЈСЃС‚Р°РЅРѕРІРёС‚Рµ EasyOCR:\n"
                f"```pip install easyocr```\n\n"
                f"File ID: `{order.payment_screenshot}`\n"
                f"Р’СЂСѓС‡РЅСѓСЋ РїСЂРѕРІРµСЂСЊС‚Рµ СЃРєСЂРёРЅС€РѕС‚ РЅР° РЅР°Р»РёС‡РёРµ РѕРїР»Р°С‚С‹ 777 в‚Ѕ.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.message.answer(
                f"вќЊ *РћС€РёР±РєР° РїСЂРё РѕР±СЂР°Р±РѕС‚РєРµ СЃРєСЂРёРЅС€РѕС‚Р°:*\n```{str(e)[:500]}```",
                parse_mode="Markdown"
            )


@router.message(Command("admin_drafts"))
async def cmd_admin_drafts(message: Message):
    """РџСЂРѕСЃРјРѕС‚СЂ С‡РµСЂРЅРѕРІРёРєРѕРІ, РѕР¶РёРґР°СЋС‰РёС… РїСЂРѕРІРµСЂРєРё С‡РµР»РѕРІРµРєРѕРј"""
    if not is_admin(message.from_user.id):
        await message.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.")
        return
    
    async with get_session_maker()() as session:
        # РџРѕР»СѓС‡Р°РµРј С‡РµСЂРЅРѕРІРёРєРё, РѕР¶РёРґР°СЋС‰РёРµ РїСЂРѕРІРµСЂРєРё
        pending_drafts = await HybridDraftService.get_pending_drafts(session, limit=20)
        
        if not pending_drafts:
            await message.answer("вњ… *РќРµС‚ С‡РµСЂРЅРѕРІРёРєРѕРІ, РѕР¶РёРґР°СЋС‰РёС… РїСЂРѕРІРµСЂРєРё.*", parse_mode="Markdown")
            return
        
        # РџРѕРєР°Р·С‹РІР°РµРј СЃРїРёСЃРѕРє С‡РµСЂРЅРѕРІРёРєРѕРІ
        response = "рџ“‹ *Р§РµСЂРЅРѕРІРёРєРё РЅР° РїСЂРѕРІРµСЂРєСѓ:*\n\n"
        for draft in pending_drafts:
            response += f"рџ†” *Р§РµСЂРЅРѕРІРёРє #{draft.id}*\n"
            response += f"рџ‘¤ РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {draft.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'} (@{draft.username or 'РЅРµС‚'})\n"
            response += f"вќ“ Р’РѕРїСЂРѕСЃ: {draft.question[:100]}...\n"
            response += f"рџ•’ РЎРѕР·РґР°РЅ: {draft.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += "вЂ”" * 30 + "\n"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Р”Р»СЏ РєР°Р¶РґРѕРіРѕ С‡РµСЂРЅРѕРІРёРєР° СЃРѕР·РґР°РµРј inline-РєРЅРѕРїРєРё
        for draft in pending_drafts:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="рџ‘Ђ РџСЂРѕСЃРјРѕС‚СЂРµС‚СЊ", callback_data=f"view_draft:{draft.id}"),
                types.InlineKeyboardButton(text="вњ… РћРґРѕР±СЂРёС‚СЊ", callback_data=f"approve_draft:{draft.id}")
            )
            builder.row(
                types.InlineKeyboardButton(text="вњЏпёЏ Р РµРґР°РєС‚РёСЂРѕРІР°С‚СЊ", callback_data=f"edit_draft_admin:{draft.id}"),
                types.InlineKeyboardButton(text="вќЊ РћС‚РєР»РѕРЅРёС‚СЊ", callback_data=f"reject_draft:{draft.id}")
            )
            
            draft_text = (
                f"рџ†” *Р§РµСЂРЅРѕРІРёРє #{draft.id}*\n"
                f"рџ‘¤ РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {draft.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'} (@{draft.username or 'РЅРµС‚'})\n"
                f"вќ“ Р’РѕРїСЂРѕСЃ: {draft.question[:200]}..."
            )
            await message.answer(draft_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("view_draft:"))
async def handle_view_draft(callback: CallbackQuery):
    """РџСЂРѕСЃРјРѕС‚СЂ РґРµС‚Р°Р»РµР№ С‡РµСЂРЅРѕРІРёРєР°"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        
        if not draft:
            await callback.answer("вќЊ Р§РµСЂРЅРѕРІРёРє РЅРµ РЅР°Р№РґРµРЅ.", show_alert=True)
            return
        
        details = (
            f"рџ“‹ *Р”РµС‚Р°Р»Рё С‡РµСЂРЅРѕРІРёРєР° #{draft.id}*\n\n"
            f"рџ‘¤ *РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ:*\n"
            f"вЂў ID: {draft.user_id}\n"
            f"вЂў РРјСЏ: {draft.first_name or 'РќРµРёР·РІРµСЃС‚РЅРѕ'}\n"
            f"вЂў Username: @{draft.username or 'РЅРµС‚'}\n\n"
            f"вќ“ *Р’РѕРїСЂРѕСЃ:*\n{draft.question}\n\n"
            f"рџ¤– *Р§РµСЂРЅРѕРІРёРє РР:*\n{draft.ai_draft[:2000]}"
        )
        if len(draft.ai_draft) > 2000:
            details += "\n... (С‚РµРєСЃС‚ РѕР±СЂРµР·Р°РЅ)"
        
        details += f"\n\nрџ“Љ *РЎС‚Р°С‚СѓСЃ:* {draft.status.value}"
        if draft.reviewer_id:
            details += f"\nрџ‘ЁвЂЌрџ’ј *РџСЂРѕРІРµСЂСЏСЋС‰РёР№:* {draft.reviewer_id}"
        if draft.reviewer_notes:
            details += f"\nрџ“ќ *Р—Р°РјРµС‚РєРё РїСЂРѕРІРµСЂСЏСЋС‰РµРіРѕ:*\n{draft.reviewer_notes}"
        
        details += f"\n\nрџ•’ *РЎРѕР·РґР°РЅ:* {draft.created_at.strftime('%d.%m.%Y %H:%M')}"
        if draft.reviewed_at:
            details += f"\nвњЏпёЏ *РџСЂРѕРІРµСЂРµРЅ:* {draft.reviewed_at.strftime('%d.%m.%Y %H:%M')}"
        
        await callback.answer()
        await callback.message.answer(details, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("approve_draft:"))
async def handle_approve_draft(callback: CallbackQuery):
    """РћРґРѕР±СЂРµРЅРёРµ С‡РµСЂРЅРѕРІРёРєР° (РѕС‚РїСЂР°РІРєР° РєР°Рє РµСЃС‚СЊ)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.approve_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=callback.from_user.id,
            final_answer=None,  # РѕС‚РїСЂР°РІР»СЏРµРј РєР°Рє РµСЃС‚СЊ
            reviewer_notes="РћРґРѕР±СЂРµРЅРѕ Р±РµР· РёР·РјРµРЅРµРЅРёР№."
        )
        
        if not draft:
            await callback.answer("вќЊ Р§РµСЂРЅРѕРІРёРє РЅРµ РЅР°Р№РґРµРЅ.", show_alert=True)
            return
        
        # РћС‚РїСЂР°РІР»СЏРµРј РѕС‚РІРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ
        try:
            await callback.bot.send_message(
                chat_id=draft.user_id,
                text=f"вњ… *Р’Р°С€ С‡РµСЂРЅРѕРІРёРє РїСЂРѕРІРµСЂРµРЅ*\n\n{draft.final_answer}",
                parse_mode="Markdown"
            )
            # РџРѕРјРµС‡Р°РµРј РєР°Рє РѕС‚РїСЂР°РІР»РµРЅРЅС‹Р№
            await HybridDraftService.mark_as_sent(session, draft_id)
            await callback.answer("вњ… Р§РµСЂРЅРѕРІРёРє РѕРґРѕР±СЂРµРЅ Рё РѕС‚РїСЂР°РІР»РµРЅ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.")
            
            # РћР±РЅРѕРІР»СЏРµРј СЃРѕРѕР±С‰РµРЅРёРµ
            await callback.message.edit_text(
                f"вњ… *Р§РµСЂРЅРѕРІРёРє #{draft_id} РѕРґРѕР±СЂРµРЅ Рё РѕС‚РїСЂР°РІР»РµРЅ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.*",
                parse_mode="Markdown"
            )
        except Exception as e:
            log.error(f"РћС€РёР±РєР° РїСЂРё РѕС‚РїСЂР°РІРєРµ С‡РµСЂРЅРѕРІРёРєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ: {e}")
            await callback.answer("вњ… Р§РµСЂРЅРѕРІРёРє РѕРґРѕР±СЂРµРЅ, РЅРѕ РЅРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("edit_draft_admin:"))
async def handle_edit_draft_admin(callback: CallbackQuery, state: FSMContext):
    """РќР°С‡Р°Р»Рѕ СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРёСЏ С‡РµСЂРЅРѕРІРёРєР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    # РЎРѕС…СЂР°РЅСЏРµРј draft_id РІ СЃРѕСЃС‚РѕСЏРЅРёРё
    await state.update_data(admin_edit_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"вњЏпёЏ *Р РµРґР°РєС‚РёСЂРѕРІР°РЅРёРµ С‡РµСЂРЅРѕРІРёРєР° #{draft_id}*\n\n"
        "РћС‚РїСЂР°РІСЊС‚Рµ РёСЃРїСЂР°РІР»РµРЅРЅС‹Р№ С‚РµРєСЃС‚ РѕС‚РІРµС‚Р°. Р’С‹ РјРѕР¶РµС‚Рµ РїРѕР»РЅРѕСЃС‚СЊСЋ РёР·РјРµРЅРёС‚СЊ С‚РµРєСЃС‚ РёР»Рё РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°С‚СЊ С‡Р°СЃС‚РёС‡РЅРѕ.\n\n"
        "РљРѕРіРґР° Р·Р°РєРѕРЅС‡РёС‚Рµ вЂ” РїСЂРѕСЃС‚Рѕ РѕС‚РїСЂР°РІСЊС‚Рµ СЃРѕРѕР±С‰РµРЅРёРµ.",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_edited_draft(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРЅРѕРіРѕ С‡РµСЂРЅРѕРІРёРєР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј"""
    data = await state.get_data()
    draft_id = data.get("admin_edit_draft_id")
    
    if not draft_id:
        # РќРµ СЂРµРґР°РєС‚РёСЂСѓРµРј С‡РµСЂРЅРѕРІРёРє, РІРѕР·РјРѕР¶РЅРѕ СЌС‚Рѕ РґСЂСѓРіРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ
        return
    
    edited_text = message.text.strip()
    if not edited_text:
        await message.answer("вќЊ РўРµРєСЃС‚ РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚С‹Рј.")
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.approve_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=message.from_user.id,
            final_answer=edited_text,
            reviewer_notes="РћС‚СЂРµРґР°РєС‚РёСЂРѕРІР°РЅРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј."
        )
        
        if not draft:
            await message.answer("вќЊ Р§РµСЂРЅРѕРІРёРє РЅРµ РЅР°Р№РґРµРЅ.")
            await state.clear()
            return
        
        # РћС‚РїСЂР°РІР»СЏРµРј РѕС‚РІРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ
        try:
            await message.bot.send_message(
                chat_id=draft.user_id,
                text=f"вњ… *Р’Р°С€ С‡РµСЂРЅРѕРІРёРє РїСЂРѕРІРµСЂРµРЅ Рё РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°РЅ*\n\n{draft.final_answer}",
                parse_mode="Markdown"
            )
            # РџРѕРјРµС‡Р°РµРј РєР°Рє РѕС‚РїСЂР°РІР»РµРЅРЅС‹Р№
            await HybridDraftService.mark_as_sent(session, draft_id)
            await message.answer(f"вњ… Р§РµСЂРЅРѕРІРёРє #{draft_id} РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°РЅ Рё РѕС‚РїСЂР°РІР»РµРЅ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.")
        except Exception as e:
            log.error(f"РћС€РёР±РєР° РїСЂРё РѕС‚РїСЂР°РІРєРµ С‡РµСЂРЅРѕРІРёРєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ: {e}")
            await message.answer("вњ… Р§РµСЂРЅРѕРІРёРє РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°РЅ, РЅРѕ РЅРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.")
    
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("reject_draft:"))
async def handle_reject_draft(callback: CallbackQuery, state: FSMContext):
    """РћС‚РєР»РѕРЅРµРЅРёРµ С‡РµСЂРЅРѕРІРёРєР°"""
    if not is_admin(callback.from_user.id):
        await callback.answer("в›”пёЏ Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰С‘РЅ.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("вќЊ РћС€РёР±РєР° С„РѕСЂРјР°С‚Р°.", show_alert=True)
        return
    
    # РЎРѕС…СЂР°РЅСЏРµРј draft_id РІ СЃРѕСЃС‚РѕСЏРЅРёРё Рё РїСЂРѕСЃРёРј РїСЂРёС‡РёРЅСѓ РѕС‚РєР»РѕРЅРµРЅРёСЏ
    await state.update_data(admin_reject_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"вќЊ *РћС‚РєР»РѕРЅРµРЅРёРµ С‡РµСЂРЅРѕРІРёРєР° #{draft_id}*\n\n"
        "РЈРєР°Р¶РёС‚Рµ РїСЂРёС‡РёРЅСѓ РѕС‚РєР»РѕРЅРµРЅРёСЏ (СЌС‚Рѕ Р±СѓРґРµС‚ СЃРѕС…СЂР°РЅРµРЅРѕ РІ Р·Р°РјРµС‚РєР°С…):",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_reject_reason(message: Message, state: FSMContext):
    """РћР±СЂР°Р±РѕС‚С‡РёРє РїСЂРёС‡РёРЅС‹ РѕС‚РєР»РѕРЅРµРЅРёСЏ С‡РµСЂРЅРѕРІРёРєР°"""
    data = await state.get_data()
    draft_id = data.get("admin_reject_draft_id")
    
    if not draft_id:
        # РќРµ РѕС‚РєР»РѕРЅСЏРµРј С‡РµСЂРЅРѕРІРёРє, РІРѕР·РјРѕР¶РЅРѕ СЌС‚Рѕ РґСЂСѓРіРѕРµ СЃРѕРѕР±С‰РµРЅРёРµ
        return
    
    reason = message.text.strip()
    if not reason:
        await message.answer("вќЊ РџСЂРёС‡РёРЅР° РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РїСѓСЃС‚РѕР№.")
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.reject_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=message.from_user.id,
            reviewer_notes=reason
        )
        
        if not draft:
            await message.answer("вќЊ Р§РµСЂРЅРѕРІРёРє РЅРµ РЅР°Р№РґРµРЅ.")
            await state.clear()
            return
        
        # РЈРІРµРґРѕРјР»СЏРµРј РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РѕР± РѕС‚РєР»РѕРЅРµРЅРёРё
        try:
            await message.bot.send_message(
                chat_id=draft.user_id,
                text=f"вќЊ *Р’Р°С€ С‡РµСЂРЅРѕРІРёРє РѕС‚РєР»РѕРЅС‘РЅ*\n\n"
                     f"РџСЂРёС‡РёРЅР°: {reason}\n\n"
                     f"Р’С‹ РјРѕР¶РµС‚Рµ Р·Р°РґР°С‚СЊ РЅРѕРІС‹Р№ РІРѕРїСЂРѕСЃ РёР»Рё РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°С‚СЊ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёР№.",
                parse_mode="Markdown"
            )
            await message.answer(f"вњ… Р§РµСЂРЅРѕРІРёРє #{draft_id} РѕС‚РєР»РѕРЅС‘РЅ. РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ СѓРІРµРґРѕРјР»С‘РЅ.")
        except Exception as e:
            log.error(f"РћС€РёР±РєР° РїСЂРё СѓРІРµРґРѕРјР»РµРЅРёРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ: {e}")
            await message.answer(f"вњ… Р§РµСЂРЅРѕРІРёРє #{draft_id} РѕС‚РєР»РѕРЅС‘РЅ, РЅРѕ РЅРµ СѓРґР°Р»РѕСЃСЊ СѓРІРµРґРѕРјРёС‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.")
    
    await state.clear()