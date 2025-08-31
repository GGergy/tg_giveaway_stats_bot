from telebot.states import StatesGroup, State


class CreateEventStates(StatesGroup):
    id = State()
    title = State()
    welcome_text = State()


class UpdateEventStates(StatesGroup):
    set_title = State()
    set_description = State()


class ScheduleMailingStates(StatesGroup):
    get_date = State()
    get_text = State()
    update_date = State()
    update_text = State()


class SingleStates(StatesGroup):
    get_qnare_comment = State()
    get_mailing_text = State()
    get_sql_command = State()
