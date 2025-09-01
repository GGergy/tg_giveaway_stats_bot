from datetime import datetime

from pyrogram import Client, filters, types
import pyrostep

from utils.config import settings
from utils.callback_io import call_out, filter_generator, CallbackDataManager
from utils.parse import parse_date, parse_links
from utils.db.models import User, conn, Giveaway, Channel
from utils.textutil import (gettext,
    # find_usages
                            )

# find_usages(__file__, funcname="gettext")
app = Client(
    name=settings.bot_name,
    api_id=settings.api_id,
    api_hash=settings.api_hash,
    bot_token=settings.tg_bot_token,
)
pyrostep.listen(app)

only_delete_kb = types.InlineKeyboardMarkup(
    inline_keyboard=[[types.InlineKeyboardButton(text=gettext("close"), callback_data=call_out("close"))]],
)


async def title_by_username(username):
    res = await app.get_chat("@" + username)
    res = res.title
    if not res:
        return username
    return res


@app.on_message(filters=filters.command("start"))
async def start(_, message: types.Message):
    with conn() as session:
        if not session.get(User, message.chat.id):
            session.add(User(id=message.chat.id, username=message.chat.username))
            session.commit()
    await app.send_message(chat_id=message.chat.id, text=gettext("hello"), reply_markup=only_delete_kb)
    await app.delete_messages(chat_id=message.chat.id, message_ids=[message.id])


@app.on_message(filters=lambda _, message: message.forward_from_message_id)
async def parse(_, message: types.Message):
    try:
        date = parse_date(message)
    except ValueError:
        date = settings.default_date

    links = parse_links(message)
    with conn() as session:
        if session.query(Giveaway).filter_by(user_id=message.chat.id, message_id=message.forward_from_message_id,
                                             chat_id=message.forward_from_chat.id).count() > 0:
            mk = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=gettext("close"),
                                                                                         callback_data=call_out(
                                                                                             "close"))]])
            await message.reply(text=gettext("giveaway_exists"), reply_markup=mk, reply_to_message_id=message.id)
            return
        title = gettext("giveaway_from", title=", ".join(map(lambda x: "@" + x, links)))
        giveaway = Giveaway(user_id=message.chat.id, chat_id=message.forward_from_chat.id,
                            message_id=message.forward_from_message_id, title=title, end_date=date)
        session.add(giveaway)
        for link in links:
            channel = session.get(Channel, link)
            if not channel:
                channel = Channel(name=link)
                session.add(channel)
            giveaway.channels.append(channel)
        session.commit()
    giveaway = session.query(Giveaway).filter_by(user_id=message.chat.id, message_id=message.forward_from_message_id,
                                                 chat_id=message.forward_from_chat.id).first()
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=gettext("change_date_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_date",
                                                                                     giveaway_id=giveaway.id))],
                                                     [types.InlineKeyboardButton(text=gettext("change_channels_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_channels",
                                                                                     giveaway_id=giveaway.id))]])
    await message.reply(reply_markup=kb, disable_web_page_preview=True, reply_to_message_id=message.id,
                        text=gettext("edit_giveaway",
                                     date=date.strftime("%d.%m.%Y") if date > settings.default_date else gettext(
                                         "date_not_parsed"),
                                     channels="\n".join(map(lambda x: "@" + x, links))))


@app.on_callback_query(filter_generator("change_date"))
async def edit_date(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("giveaway_id", typeof=int)

    await call.message.edit(text=gettext("Enter_new_date"))
    date = None
    while not date:
        try:
            msg = await pyrostep.wait_for(call.message.chat.id, timeout=settings.pyro_timeout)
            await app.delete_messages(chat_id=call.message.chat.id, message_ids=[msg.id])
        except TimeoutError:
            await app.answer_callback_query(call.id, text=gettext("timed_out"), show_alert=True)
            await app.delete_messages(chat_id=call.message.chat.id, message_ids=[call.message.id])
            return
        try:
            date = datetime.strptime(msg.text, "%d.%m.%Y")
        except ValueError:
            await call.message.edit(text=gettext("invalid_date", date=msg.text))
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        giveaway.end_date = date
        print(date)
        session.commit()
    mk = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text=gettext("back_to_gw_b"),
                                                                 callback_data=call_out("giveaway_setup",
                                                                                        giveaway_id=giveaway_id))]])
    await call.message.edit(text=gettext("date_changed"), reply_markup=mk)


@app.on_callback_query(filter_generator("change_channels"))
async def edit_channels(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("giveaway_id", typeof=int)
    mk = types.InlineKeyboardMarkup(inline_keyboard=[])
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        for channel in giveaway.channels:
            title = await title_by_username(channel.name)
            mk.inline_keyboard.append(
                [types.InlineKeyboardButton(text=title, callback_data=call_out("pass")),
                 types.InlineKeyboardButton(text=gettext("delete_channel_b"),
                                            callback_data=call_out("delete_channel",
                                                                   gw_id=giveaway_id,
                                                                   ch_id=channel.name))])
            await title_by_username(channel.name)
        mk.inline_keyboard.append([types.InlineKeyboardButton(text=gettext("add_channel_b"),
                                                              callback_data=call_out("add_channel",
                                                                                     gw_id=giveaway_id)),
                                   types.InlineKeyboardButton(text=gettext("back_to_gw_b"),
                                                              callback_data=call_out("giveaway_setup",
                                                                                     giveaway_id=giveaway_id))])
        await call.message.edit(text=gettext("edit_channels_t"), reply_markup=mk)


@app.on_callback_query(filter_generator("giveaway_setup"))
async def back_to_gw(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("giveaway_id", typeof=int)
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        links = [channel.name for channel in giveaway.channels]
        date = giveaway.end_date
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=gettext("change_date_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_date",
                                                                                     giveaway_id=giveaway.id))],
                                                     [types.InlineKeyboardButton(text=gettext("change_channels_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_channels",
                                                                                     giveaway_id=giveaway.id))]])
    await call.message.edit(reply_markup=kb, disable_web_page_preview=True,
                            text=gettext("edit_giveaway",
                                         date=date.strftime("%d.%m.%Y") if date > settings.default_date else gettext(
                                             "date_not_parsed"),
                                         channels="\n".join(map(lambda x: "@" + x, links))))


@app.on_callback_query(filters=filter_generator("close"))
async def close(_, call: types.CallbackQuery):
    await app.answer_callback_query(call.id)
    t_d = [call.message.id]
    if call.message.reply_to_message_id:
        t_d.append(call.message.reply_to_message_id)
    await app.delete_messages(chat_id=call.message.chat.id, message_ids=t_d)


@app.on_message()
async def deleter(_, message: types.Message):
    await app.delete_messages(chat_id=message.chat.id, message_ids=[message.id])


app.run()
