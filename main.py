from datetime import datetime

from pyrogram import Client, filters, types, errors
import pyrostep
from sqlalchemy.orm import load_only

from utils.config import settings
from utils.callback_io import call_out, filter_generator, CallbackDataManager
from utils.parse import parse_date, parse_links
from utils.db.models import User, conn, Giveaway, Channel
from utils.textutil import (gettext, truncate,
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
    try:
        res = await app.get_chat("@" + username)
        return res.title
    except KeyError:
        return "@" + username


@app.on_message(filters=filters.command("start"))
async def start(_, message: types.Message):
    with conn() as session:
        if not session.get(User, message.chat.id):
            session.add(User(id=message.chat.id, username=message.chat.username))
            session.commit()
    await app.send_message(chat_id=message.chat.id, text=gettext("hello"), reply_markup=only_delete_kb)
    await message.delete()


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
            link = link.lower()
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
                                                                                     giveaway_id=giveaway.id))],
                                                     [types.InlineKeyboardButton(text=gettext("close"),
                                                                                 callback_data=call_out("close"))]])
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
            await app.answer_callback_query(callback_query_id=call.id, text=gettext("timed_out"), show_alert=True)
            await call.message.delete()
            if call.message.reply_to_message_id:
                await app.delete_messages(chat_id=call.message.chat.id, message_ids=[call.message.reply_to_message_id])
            return
        if msg.text == "-":
            break
        try:
            date = datetime.strptime(msg.text, "%d.%m.%Y")
        except ValueError:
            await call.message.edit(text=gettext("invalid_date", date=msg.text))
    else:
        with conn() as session:
            giveaway = session.get(Giveaway, giveaway_id)
            giveaway.end_date = date
            session.commit()
    mk = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text=gettext("back"),
                                                                 callback_data=call_out("giveaway_setup",
                                                                                        giveaway_id=giveaway_id))]])
    await call.message.edit(text=gettext("date_changed" if date else "date_kept"), reply_markup=mk)


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
        mk.inline_keyboard.append([types.InlineKeyboardButton(text=gettext("add_channel_b"),
                                                              callback_data=call_out("add_channel",
                                                                                     gw_id=giveaway_id)),
                                   types.InlineKeyboardButton(text=gettext("back"),
                                                              callback_data=call_out("giveaway_setup",
                                                                                     giveaway_id=giveaway_id))])
        await call.message.edit(text=gettext("edit_channels_t"), reply_markup=mk)


@app.on_callback_query(filter_generator("delete_channel"))
async def delete_channel(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("gw_id", typeof=int)
        channel_id = mgr.get("ch_id", typeof=str)
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        channel = session.get(Channel, channel_id)
        giveaway.channels.remove(channel)
        session.commit()
    mk = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text=gettext("back"),
                                                                 callback_data=call_out("change_channels",
                                                                                        giveaway_id=giveaway_id))]])
    await call.message.edit(text=gettext("channel_deleted"), reply_markup=mk)


@app.on_callback_query(filter_generator("add_channel"))
async def add_channel(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("gw_id", typeof=int)
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        channels = [channel.name for channel in giveaway.channels]
    name = None
    await call.message.edit(text=gettext("enter_new_channel"))
    while not name:
        try:
            msg = await pyrostep.wait_for(call.message.chat.id, timeout=settings.pyro_timeout)
            await app.delete_messages(chat_id=call.message.chat.id, message_ids=[msg.id])
        except TimeoutError:
            await app.answer_callback_query(callback_query_id=call.id, text=gettext("timed_out"), show_alert=True)
            await call.message.delete()
            if call.message.reply_to_message_id:
                await app.delete_messages(chat_id=call.message.chat.id, message_ids=[call.message.reply_to_message_id])
            return
        if msg.text == "-":
            break
        links = parse_links(msg)
        if not links:
            await call.message.edit(text=gettext("link_not_found"))
        else:
            link = links[0].lower()
            if link not in channels:
                name = link
            else:
                await call.message.edit(text=gettext("link_already_exists"))
    else:
        with conn() as session:
            channel = session.get(Channel, name)
            if not channel:
                channel = Channel(name=name)
                session.add(channel)
            giveaway = session.get(Giveaway, giveaway_id)
            giveaway.channels.append(channel)
            session.commit()
    mk = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text=gettext("back"),
                                                                 callback_data=call_out("change_channels",
                                                                                        giveaway_id=giveaway_id))]])
    await call.message.edit(text=gettext("channel_added" if name else "channel_not_added"), reply_markup=mk)


@app.on_callback_query(filter_generator("giveaway_setup"))
async def back_to_gw(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        giveaway_id = mgr.get("giveaway_id", typeof=int)
        send_msg = mgr.get("send_msg", typeof=bool)
    with conn() as session:
        giveaway = session.get(Giveaway, giveaway_id)
        if not giveaway:
            await app.answer_callback_query(call.id, text=gettext("giveaway_not_found"))
            return
        links = [channel.name for channel in giveaway.channels]
        date = giveaway.end_date
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=gettext("change_date_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_date",
                                                                                     giveaway_id=giveaway.id))],
                                                     [types.InlineKeyboardButton(text=gettext("change_channels_b"),
                                                                                 callback_data=call_out(
                                                                                     "change_channels",
                                                                                     giveaway_id=giveaway.id))],
                                                     [types.InlineKeyboardButton(text=gettext("close"),
                                                                                 callback_data=call_out("close"))]])
    text = gettext("edit_giveaway",
                   date=date.strftime("%d.%m.%Y") if date > settings.default_date else gettext(
                       "date_not_parsed"),
                   channels="\n".join(map(lambda x: "@" + x, links)))
    await app.answer_callback_query(call.id)
    print(errors.BadRequest.__class__)
    if send_msg:
        try:
            msg = await app.forward_messages(call.message.chat.id, giveaway.chat_id, [giveaway.message_id])
            await call.message.reply(text=text, reply_markup=kb, disable_web_page_preview=True,
                                     reply_to_message_id=msg[0].id)
        except errors.exceptions.bad_request_400:
            await call.message.reply(text=text, reply_markup=kb, disable_web_page_preview=True)
        return
    await call.message.edit(reply_markup=kb, disable_web_page_preview=True, text=text)


@app.on_message(filters.command("menu"))
async def menu(_, message: types.Message):
    with conn() as session:
        user = session.get(User, message.chat.id)
        is_notify = gettext("notify") if user.notifies else gettext("no_notify")
    mk = types.InlineKeyboardMarkup(
        [[types.InlineKeyboardButton(text=gettext("my_giveaways_b"), callback_data=call_out("my_giveaways"))],
         [types.InlineKeyboardButton(text=gettext("my_channels_b"), callback_data=call_out("my_channels"))],
         [types.InlineKeyboardButton(text=gettext("notify_b") + is_notify, callback_data=call_out("switch_notify"))]])
    await message.reply(text=gettext("menu_text"), reply_markup=mk)
    await message.delete()


@app.on_callback_query(filter_generator("my_giveaways"))
async def choose_gwlist_type(_, call: types.CallbackQuery):
    mk = types.InlineKeyboardMarkup(
        [
            [types.InlineKeyboardButton(text=gettext("my_active_gw"), callback_data=call_out("gw_list", p=1, a=True))],
            [types.InlineKeyboardButton(text=gettext("my_archived_gw"),
                                        callback_data=call_out("gw_list", p=1, a=False))]
        ]
    )
    await call.message.edit(text=gettext("choose_gwlist_type"), reply_markup=mk)


@app.on_callback_query(filter_generator("gw_list"))
async def display_giveaways(_, call: types.CallbackQuery):
    with CallbackDataManager(call.data) as mgr:
        is_active = mgr.get("a", typeof=bool)
        page = mgr.get("p", typeof=int)
    if page < 1:
        await app.answer_callback_query(call.id, text=gettext("page_empty"), show_alert=True)
        return
    with conn() as session:
        giveaways = session.query(Giveaway).filter_by(user_id=call.message.chat.id, archived=not is_active).options(
            load_only(Giveaway.title, Giveaway.end_date)).order_by(Giveaway.end_date.asc())[
            (page - 1) * settings.page_size: page * settings.page_size]
    if not giveaways:
        await app.answer_callback_query(call.id, text=gettext("page_empty"), show_alert=True)
        return
    mk = types.InlineKeyboardMarkup([])
    for giveaway in giveaways:
        end = giveaway.end_date
        if end == settings.default_date:
            end = gettext("date_not_parsed")
        else:
            end = end.strftime("%d.%m.%Y")
        mk.inline_keyboard.append([types.InlineKeyboardButton(
            text=gettext("gw_button", title=truncate(giveaway.title, 30), end=end),
            callback_data=call_out("giveaway_setup", giveaway_id=giveaway.id, send_msg=True))])
    mk.inline_keyboard.append(
        [types.InlineKeyboardButton(text=gettext("prev_b"),
                                    callback_data=call_out("gw_list", a=is_active, p=page - 1)),
         types.InlineKeyboardButton(text=gettext("next_b"),
                                    callback_data=call_out("gw_list", a=is_active, p=page + 1)),
         types.InlineKeyboardButton(text=gettext("back"),
                                    callback_data=call_out("my_giveaways"))])

    await call.message.edit(text=gettext("your_active_gw" if is_active else "your_archived_gw"), reply_markup=mk)


@app.on_callback_query(filter_generator("switch_notify"))
async def switch_notify(_, call: types.CallbackQuery):
    with conn() as session:
        user = session.get(User, call.message.chat.id)
        user.notifies = not user.notifies
        is_notify = gettext("notify") if user.notifies else gettext("no_notify")
        session.commit()
    notify_b = types.InlineKeyboardButton(text=gettext("notify_b") + is_notify, callback_data=call_out("switch_notify"))
    mk = call.message.reply_markup
    mk.inline_keyboard[-1] = [notify_b]
    await call.message.edit_reply_markup(mk)


@app.on_callback_query(filters=filter_generator("close"))
async def close(_, call: types.CallbackQuery):
    await app.answer_callback_query(call.id)
    t_d = [call.message.id]
    if call.message.reply_to_message_id:
        t_d.append(call.message.reply_to_message_id)
    await app.delete_messages(chat_id=call.message.chat.id, message_ids=t_d)


@app.on_message()
async def deleter(_, message: types.Message):
    await message.delete()


app.run()
