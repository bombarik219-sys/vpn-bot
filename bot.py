import asyncio
import os
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from servers import PLANS, SERVERS, REGIONS, find_plan, find_server
from storage import (
    init_db, is_active, is_lifetime, days_left,
    add_subscription, remove_subscription, get_subscription,
    is_banned, ban_user, unban_user, get_ban_info,
    is_admin, add_admin, remove_admin, list_admins,
    get_stats, get_all_user_ids,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def is_admin_user(user_id: int) -> bool:
    if ADMIN_ID and user_id == ADMIN_ID:
        return True
    return is_admin(user_id)


# ---------- Клавиатуры ----------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Серверы", callback_data="servers")],
        [InlineKeyboardButton(text="💳 Подписка", callback_data="subscription")],
    ])


def regions_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=r["name"], callback_data=f"reg:{rid}")]
        for rid, r in REGIONS.items()
    ]
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def servers_keyboard(region_id: str) -> InlineKeyboardMarkup:
    region = REGIONS.get(region_id)
    if not region:
        return InlineKeyboardMarkup(inline_keyboard=[])
    buttons = []
    for sid in region["server_ids"]:
        srv = find_server(sid)
        if srv:
            buttons.append([InlineKeyboardButton(
                text=srv["name"], callback_data=f"srv:{sid}",
            )])
    buttons.append([InlineKeyboardButton(text="« К регионам", callback_data="servers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def plans_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{p['name']} — {p['price']} ⭐",
            callback_data=f"plan:{p['id']}",
        )]
        for p in PLANS
    ]
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def buy_keyboard(plan_id: str, price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Оплатить {price} ⭐", callback_data=f"buy:{plan_id}",
        )],
        [InlineKeyboardButton(text="« К тарифам", callback_data="subscription")],
    ])


def status_line(user_id: int) -> str:
    if is_banned(user_id):
        return "🚫 <b>Вы забанены</b>"
    if is_lifetime(user_id):
        return "♾ <b>Подписка «Навсегда» активна</b>"
    if is_active(user_id):
        return f"✅ Подписка активна, осталось <b>{days_left(user_id)} дн.</b>"
    return "❌ Подписка не активна"


# ---------- Пользовательские хэндлеры ----------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if is_banned(message.from_user.id):
        await message.answer("🚫 Вы забанены. Доступ к боту закрыт.")
        return
    user_id = message.from_user.id
    text = (
        "🌐 <b>VPN-бот</b>\n\n"
        f"{status_line(user_id)}\n\n"
        "Доступ ко всем серверам по подписке:\n"
        "• 1 месяц — 75 ⭐\n"
        "• 2 месяца — 150 ⭐\n"
        "• 1 год — 900 ⭐\n"
        "• Навсегда — 1590 ⭐\n\n"
        "📲 Приложение Happ: https://happ.su"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Как это работает:</b>\n\n"
        "1. Открой «💳 Подписка» и выбери тариф\n"
        "2. Оплати звёздами Telegram\n"
        "3. Зайди в «🌐 Серверы» и добавь ссылку в Happ"
    )


@dp.callback_query(F.data == "main_menu")
async def on_main_menu(callback: CallbackQuery):
    if is_banned(callback.from_user.id):
        await callback.answer("Вы забанены", show_alert=True)
        return
    user_id = callback.from_user.id
    text = f"🌐 <b>VPN-бот</b>\n\n{status_line(user_id)}\n\nВыбери раздел:"
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "servers")
async def on_servers(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_banned(user_id):
        await callback.answer("Вы забанены", show_alert=True)
        return
    if not is_active(user_id):
        text = "🔒 <b>Серверы недоступны</b>\n\nОформи подписку."
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 К тарифам", callback_data="subscription")],
                [InlineKeyboardButton(text="« Назад", callback_data="main_menu")],
            ]),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"🌐 <b>Выбери регион</b>\n\nДоступно серверов: {len(SERVERS)}",
        reply_markup=regions_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("reg:"))
async def on_region(callback: CallbackQuery):
    region_id = callback.data.split(":", 1)[1]
    region = REGIONS.get(region_id)
    if not region:
        await callback.answer("Регион не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"{region['name']}\n\nВыбери сервер:",
        reply_markup=servers_keyboard(region_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("srv:"))
async def on_server_chosen(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_banned(user_id):
        await callback.answer("Вы забанены", show_alert=True)
        return
    if not is_active(user_id):
        await callback.answer("Сначала оформи подписку", show_alert=True)
        return
    server_id = callback.data.split(":", 1)[1]
    server = find_server(server_id)
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    text = (
        f"✅ <b>{server['name']}</b>\n\n"
        f"Добавь эту ссылку в Happ:\n\n"
        f"<code>{server['link']}</code>\n\n"
        "📋 <b>Инструкция:</b>\n"
        "1. Скопируй ссылку (нажми на неё)\n"
        "2. Открой Happ → «+» → «Из буфера обмена»\n"
        "3. Нажми на сервер и подключись"
    )
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "subscription")
async def on_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_banned(user_id):
        await callback.answer("Вы забанены", show_alert=True)
        return
    text = (
        "💳 <b>Подписка</b>\n\n"
        f"{status_line(user_id)}\n\n"
        "Выбери тариф:\n"
        "• 1 месяц — 75 ⭐\n"
        "• 2 месяца — 150 ⭐\n"
        "• 1 год — 900 ⭐\n"
        "• Навсегда — 1590 ⭐"
    )
    await callback.message.edit_text(text, reply_markup=plans_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("plan:"))
async def on_plan_chosen(callback: CallbackQuery):
    plan_id = callback.data.split(":", 1)[1]
    plan = find_plan(plan_id)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    text = f"💳 <b>{plan['name']}</b>\n\nЦена: <b>{plan['price']} ⭐</b>\n"
    if plan["id"] == "inf":
        text += "Доступ ко всем серверам без ограничения по времени.\n"
    else:
        text += f"Длительность: {plan['days']} дней.\n"
    await callback.message.edit_text(text, reply_markup=buy_keyboard(plan_id, plan["price"]))
    await callback.answer()


@dp.callback_query(F.data.startswith("buy:"))
async def on_buy(callback: CallbackQuery):
    plan_id = callback.data.split(":", 1)[1]
    plan = find_plan(plan_id)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"VPN — {plan['name']}",
        description=f"Доступ ко всем серверам. Тариф: {plan['name']}.",
        payload=f"plan:{plan_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["name"], amount=plan["price"])],
    )
    await callback.answer()


@dp.pre_checkout_query()
async def on_pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    if not payload.startswith("plan:"):
        await message.answer("Оплата получена, но заказ не распознан.")
        return
    plan_id = payload.split(":", 1)[1]
    plan = find_plan(plan_id)
    if not plan:
        await message.answer("Оплата прошла, но тариф не найден.")
        return
    user_id = message.from_user.id
    lifetime = plan["id"] == "inf"
    add_subscription(
        user_id=user_id, days=plan["days"],
        charge_id=payment.telegram_payment_charge_id,
        amount=payment.total_amount, plan_id=plan_id, lifetime=lifetime,
    )
    if ADMIN_ID:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"💰 Оплата: {payment.total_amount} ⭐\n"
                f"Пользователь: <code>{user_id}</code>\n"
                f"Тариф: {plan['name']}",
            )
        except Exception:
            pass
    if lifetime:
        result = f"🎉 Оплата получена — {payment.total_amount} ⭐\n\n♾ Подписка <b>«Навсегда»</b> активирована!"
    else:
        result = f"🎉 Оплата получена — {payment.total_amount} ⭐\n\n✅ Тариф <b>{plan['name']}</b> активирован."
    await message.answer(result, reply_markup=main_menu_keyboard())


# ==========================================
#   АДМИН-КОМАНДЫ В TELEGRAM
# ==========================================

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin_user(message.from_user.id):
        return
    text = (
        "🛠 <b>Админ-панель</b>\n\n"
        "/give <code>user_id дней</code>\n"
        "/give_inf <code>user_id</code>\n"
        "/take <code>user_id</code>\n"
        "/ban <code>user_id [причина]</code>\n"
        "/unban <code>user_id</code>\n"
        "/info <code>user_id</code>\n"
        "/stats\n"
        "/broadcast <code>текст</code>\n"
        "/add_admin <code>user_id</code>\n"
        "/del_admin <code>user_id</code>\n"
        "/admins"
    )
    await message.answer(text)


@dp.message(Command("give"))
async def cmd_give(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /give <code>user_id дней</code>")
        return
    parts = command.args.split()
    if len(parts) != 2:
        await message.answer("Нужно 2 значения: user_id и дни.")
        return
    try:
        target_id = int(parts[0]); days = int(parts[1])
    except ValueError:
        await message.answer("Оба значения должны быть числами.")
        return
    add_subscription(target_id, days, f"admin_give_{message.from_user.id}", 0, "admin_give", False)
    await message.answer(f"✅ Выдал подписку <code>{target_id}</code> на {days} дн.")
    try:
        await bot.send_message(target_id, f"🎁 Вам выдана подписка на <b>{days} дней</b>!")
    except Exception:
        pass


@dp.message(Command("give_inf"))
async def cmd_give_inf(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /give_inf <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    add_subscription(target_id, 36500, f"admin_give_inf_{message.from_user.id}", 0, "admin_give_inf", True)
    await message.answer(f"♾ Выдал «Навсегда» пользователю <code>{target_id}</code>.")
    try:
        await bot.send_message(target_id, "🎁 Вам выдана подписка <b>«Навсегда»</b>!")
    except Exception:
        pass


@dp.message(Command("take"))
async def cmd_take(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /take <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    remove_subscription(target_id)
    await message.answer(f"🗑 Подписка <code>{target_id}</code> удалена.")


@dp.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /ban <code>user_id [причина]</code>")
        return
    parts = command.args.split(maxsplit=1)
    try:
        target_id = int(parts[0])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    reason = parts[1] if len(parts) > 1 else "без причины"
    ban_user(target_id, reason)
    await message.answer(f"🚫 <code>{target_id}</code> забанен.\nПричина: {reason}")
    try:
        await bot.send_message(target_id, f"🚫 Вы забанены.\nПричина: {reason}")
    except Exception:
        pass


@dp.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /unban <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    unban_user(target_id)
    await message.answer(f"✅ <code>{target_id}</code> разбанен.")


@dp.message(Command("info"))
async def cmd_info(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /info <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    lines = [f"👤 <b>Инфо о</b> <code>{target_id}</code>\n"]
    if is_banned(target_id):
        b = get_ban_info(target_id)
        lines.append(f"🚫 <b>Забанен</b>: {b.get('reason', 'без причины')}")
    elif is_lifetime(target_id):
        lines.append("♾ <b>Подписка «Навсегда»</b>")
    elif is_active(target_id):
        lines.append(f"✅ Подписка активна, осталось {days_left(target_id)} дн.")
    else:
        lines.append("❌ Подписки нет")
    sub = get_subscription(target_id)
    if sub:
        lines.append(f"\n💰 Всего: <b>{sub.get('total_paid', 0)}</b> ⭐")
        lines.append(f"📅 Истекает: <code>{sub.get('expires_at', '—')}</code>")
    await message.answer("\n".join(lines))


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin_user(message.from_user.id):
        return
    s = get_stats()
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{s['users']}</b>\n"
        f"✅ Активных: <b>{s['active']}</b>\n"
        f"🚫 Забанено: <b>{s['banned']}</b>\n"
        f"💳 Платежей: <b>{s['payments']}</b>\n"
        f"⭐ Звёзд: <b>{s['stars']}</b>"
    )


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /broadcast <code>текст</code>")
        return
    text = command.args
    user_ids = get_all_user_ids()
    sent = 0; failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"📢 Рассылка завершена.\nОтправлено: <b>{sent}</b>\nНе доставлено: <b>{failed}</b>")


@dp.message(Command("add_admin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /add_admin <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    add_admin(target_id)
    await message.answer(f"✅ <code>{target_id}</code> теперь админ.")


@dp.message(Command("del_admin"))
async def cmd_del_admin(message: Message, command: CommandObject):
    if not is_admin_user(message.from_user.id):
        return
    if not command.args:
        await message.answer("Формат: /del_admin <code>user_id</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return
    if target_id == ADMIN_ID:
        await message.answer("Нельзя убрать главного админа из .env.")
        return
    remove_admin(target_id)
    await message.answer(f"🗑 <code>{target_id}</code> больше не админ.")


@dp.message(Command("admins"))
async def cmd_admins(message: Message):
    if not is_admin_user(message.from_user.id):
        return
    admins = list_admins()
    lines = [f"👑 <b>Главный админ:</b> <code>{ADMIN_ID}</code>"]
    if admins:
        lines.append("\n<b>Дополнительные:</b>")
        for a in admins:
            lines.append(f"• <code>{a}</code>")
    else:
        lines.append("\nДополнительных нет.")
    await message.answer("\n".join(lines))


# ==========================================
#   КОНСОЛЬ РАЗРАБОТЧИКА (в терминале)
# ==========================================

def console_help():
    print("""
╔══════════════════════════════════════════════╗
║        КОНСОЛЬ РАЗРАБОТЧИКА                  ║
╠══════════════════════════════════════════════╣
║  help                — эта справка           ║
║  stats               — статистика            ║
║  give <id> <дней>    — выдать подписку       ║
║  giveinf <id>        — выдать «Навсегда»     ║
║  take <id>           — забрать подписку      ║
║  ban <id> [причина]  — забанить              ║
║  unban <id>          — разбанить             ║
║  info <id>           — инфо о пользователе   ║
║  admins              — список админов        ║
║  addadmin <id>       — добавить админа       ║
║  deladmin <id>       — убрать админа         ║
║  broadcast <текст>   — рассылка всем         ║
║  exit                — выйти из бота         ║
╚══════════════════════════════════════════════╝
""")


async def run_console():
    loop = asyncio.get_event_loop()
    print("\n💻 Консоль разработчика готова. Напиши 'help'.\n")

    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                await asyncio.sleep(0.1)
                continue

            cmd = line.strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=2)
            action = parts[0].lower()

            if action == "help":
                console_help()

            elif action == "stats":
                s = get_stats()
                print(f"\n📊 СТАТИСТИКА\n  👥 Пользователей: {s['users']}\n  ✅ Активных: {s['active']}\n  🚫 Забанено: {s['banned']}\n  💳 Платежей: {s['payments']}\n  ⭐ Звёзд: {s['stars']}\n")

            elif action == "give":
                if len(parts) < 3:
                    print("❌ give <user_id> <дней>")
                    continue
                try:
                    uid = int(parts[1]); days = int(parts[2])
                except ValueError:
                    print("❌ Числа нужны.")
                    continue
                add_subscription(uid, days, "console", 0, "console", False)
                print(f"✅ Выдал {uid} на {days} дн.")
                try:
                    await bot.send_message(uid, f"🎁 Подписка на <b>{days} дней</b>!")
                except Exception:
                    pass

            elif action == "giveinf":
                if len(parts) < 2:
                    print("❌ giveinf <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                add_subscription(uid, 36500, "console", 0, "console", True)
                print(f"♾ {uid} — Навсегда.")
                try:
                    await bot.send_message(uid, "🎁 Подписка <b>«Навсегда»</b>!")
                except Exception:
                    pass

            elif action == "take":
                if len(parts) < 2:
                    print("❌ take <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                remove_subscription(uid)
                print(f"🗑 {uid} — подписка удалена.")

            elif action == "ban":
                if len(parts) < 2:
                    print("❌ ban <user_id> [причина]")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                reason = parts[2] if len(parts) > 2 else "без причины"
                ban_user(uid, reason)
                print(f"🚫 {uid} забанен. {reason}")
                try:
                    await bot.send_message(uid, f"🚫 Забанен. {reason}")
                except Exception:
                    pass

            elif action == "unban":
                if len(parts) < 2:
                    print("❌ unban <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                unban_user(uid)
                print(f"✅ {uid} разбанен.")

            elif action == "info":
                if len(parts) < 2:
                    print("❌ info <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                print(f"\n👤 ИНФО {uid}")
                if is_banned(uid):
                    b = get_ban_info(uid)
                    print(f"  🚫 Забанен: {b.get('reason', '—')}")
                elif is_lifetime(uid):
                    print("  ♾ Навсегда")
                elif is_active(uid):
                    print(f"  ✅ Активна, {days_left(uid)} дн.")
                else:
                    print("  ❌ Нет подписки")
                sub = get_subscription(uid)
                if sub:
                    print(f"  💰 {sub.get('total_paid', 0)} ⭐")
                    print(f"  📅 {sub.get('expires_at', '—')}")
                print()

            elif action == "admins":
                print(f"\n👑 Главный: {ADMIN_ID}")
                admins = list_admins()
                if admins:
                    print("👥 Дополнительные:")
                    for a in admins:
                        print(f"   • {a}")
                else:
                    print("   Дополнительных нет.")
                print()

            elif action == "addadmin":
                if len(parts) < 2:
                    print("❌ addadmin <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                add_admin(uid)
                print(f"✅ {uid} теперь админ.")

            elif action == "deladmin":
                if len(parts) < 2:
                    print("❌ deladmin <user_id>")
                    continue
                try:
                    uid = int(parts[1])
                except ValueError:
                    print("❌ Число нужно.")
                    continue
                if uid == ADMIN_ID:
                    print("❌ Главного нельзя.")
                    continue
                remove_admin(uid)
                print(f"🗑 {uid} больше не админ.")

            elif action == "broadcast":
                if len(parts) < 2:
                    print("❌ broadcast <текст>")
                    continue
                text = cmd[len("broadcast "):]
                user_ids = get_all_user_ids()
                sent = 0; failed = 0
                print(f"📢 Рассылка на {len(user_ids)}...")
                for uid in user_ids:
                    try:
                        await bot.send_message(uid, text)
                        sent += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        failed += 1
                print(f"✅ Отправлено: {sent}, не доставлено: {failed}")

            elif action == "exit":
                print("👋 Выход...")
                await bot.session.close()
                os._exit(0)

            else:
                print(f"❌ Неизвестно: {action}. Напиши 'help'.")

        except Exception as e:
            print(f"⚠️ Ошибка: {e}")


# ---------- Запуск ----------

async def main():
    init_db()
    add_admin(ADMIN_ID)
    print("🤖 Бот запущен...")

    asyncio.create_task(run_console())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())