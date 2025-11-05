import os
from typing import Literal, TypedDict, cast, List

from telegram import (
    Update,
    Message,
    InputMediaVideo,
    InputMediaPhoto,
    InputMediaDocument,
    InputMediaAudio,
    error,
    Video,
)
from telegram.helpers import effective_message_type
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

from db import create_tables, check, ban, unban
from logs import get_logger

load_dotenv()
group_id = os.getenv("CHAT")
survey_id = os.getenv("CHAT_SURVEYS")
logger = get_logger()

MEDIA_GROUP_TYPES = {
    "audio": InputMediaAudio,
    "document": InputMediaDocument,
    "photo": InputMediaPhoto,
    "video": InputMediaVideo,
}


class MsgDict(TypedDict):
    media_type: Literal["video", "photo"]
    media_id: str
    caption: str
    post_id: int
    sender_id: int


async def process_exception(bot, id, err: Exception):
    logger.exception(err)
    text = "Упс! Неизвестная ошибка. Пожалуйста, свяжитесь с админинстрацией."
    await bot.send_message(id, text)


def edit_text(text: str, id: str) -> str:
    text = text.replace("/survey", "")
    text = f"Sender chat id: {id}\n\n" + text + f"\n#анкета{id}"
    return text


async def answer_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(survey_id):
        return
    full_text: str = update.message.text.replace("/answer", "")
    chat_id, reply_text = full_text.strip().split("\n", 1)
    await context.bot.send_message(chat_id, reply_text)


async def reply(bot, id):
    reply_text = (
        "Спасибо за заявку! Ваша анкета была направлена админинстраторам на проверку."
    )
    await bot.send_message(id, reply_text)


async def send_survey(message: str, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(survey_id, message)


async def send_survey_media(media, caption: str, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(media, Video):
        await context.bot.send_video(survey_id, media, caption=caption)
    else:
        await context.bot.send_photo(survey_id, media, caption)


async def send_survey_media_group(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    context.job.data = cast(List[MsgDict], context.job.data)
    media = []
    sender = context.job.data[0].get("sender_id")
    for msg_dict in context.job.data:
        caption = (
            edit_text(msg_dict["caption"], str(msg_dict["sender_id"]))
            if msg_dict["caption"]
            else msg_dict["caption"]
        )
        media.append(
            MEDIA_GROUP_TYPES[msg_dict["media_type"]](
                media=msg_dict["media_id"], caption=caption
            )
        )
    if not media:
        return
    if len(media) > 3 and sender:
        await bot.send_message(
            sender,
            "К анкете можно прикрепить не более 3 фото! Пожалуйста, отправьте анкету еще раз.",
        )
    else:
        await bot.send_media_group(survey_id, media)
        await reply(bot, sender)
        logger.debug(f"Media group processed for {sender}")


async def receive_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if check(update.message.from_user.id):
        await context.bot.send_message(update.effective_chat.id, "вы находитесь в черном списке.")
        return
    text = edit_text(update.message.text, update.effective_chat.id)
    try:
        await send_survey(text, context)
        await reply(context.bot, update.effective_chat.id)
        logger.debug(f"Text processed for {update.effective_chat.id}")
    except Exception as err:
        await process_exception(context.bot, update.effective_chat.id, err)


async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if check(update.message.from_user.id):
        await context.bot.send_message(update.effective_chat.id, "вы находитесь в черном списке.")
        return
    message: Message = update.effective_message
    try:
        if not message.media_group_id:
            text = update.message.caption
            text = edit_text(text or "", update.effective_chat.id)
            if update.message.video:
                media = update.message.video
            if update.message.photo:
                media = update.message.photo[-1]
            await send_survey_media(media, text, context)
            await reply(context.bot, update.effective_chat.id)
            logger.debug(f"Image processed for {update.effective_chat.id}")
        elif (message.photo or message.video) and message.media_group_id:
            media_type = effective_message_type(message)
            if message.photo:
                media_id = message.photo[-1].file_id
            elif message.video:
                media_id = message.video.file_id
            msg_dict = {
                "media_type": media_type,
                "media_id": media_id,
                "caption": message.caption,
                "message_id": message.message_id,
                "sender_id": update.effective_chat.id,
            }
            jobs = context.job_queue.get_jobs_by_name(str(message.media_group_id))
            if jobs:
                jobs[0].data.append(msg_dict)
            else:
                context.job_queue.run_once(
                    callback=send_survey_media_group,
                    when=10,
                    data=[msg_dict],
                    name=str(message.media_group_id),
                )
    except error.BadRequest as err:
        if "Message caption is too long" in err.message:
            await context.bot.send_message(
                update.effective_chat.id,
                "Пожалуйста, отправьте картинки отдельным сообщением!"
                "Если картинки и не было, то свяжитесь с админинстрацией. Простите!",
            )
    except Exception as err:
        await process_exception(context.bot, update.effective_chat.id, err)


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(survey_id):
        return
    if not context.args[0]:
        await context.bot.send_message(survey_id, "Укажите id юзера для бана")
        return
    try:
        res = int(context.args[0])
    except ValueError:
        await context.bot.send_message(survey_id, "id должно быть числом")
        return
    if ban(res):
        await context.bot.send_message(survey_id, f"Юзер {int(context.args[0])} забанен")
    else:
        await context.bot.send_message(survey_id, f"Ошибка бана {int(context.args[0])}")


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(survey_id):
        return
    if not context.args[0]:
        await context.bot.send_message(survey_id, "Укажите id юзера для разбана")
        return
    try:
        res = int(context.args[0])
    except ValueError:
        await context.bot.send_message(survey_id, "id должно быть числом")
        return
    if unban(res):
        await context.bot.send_message(survey_id, f"Юзер {int(context.args[0])} разбанен")
    else:
        await context.bot.send_message(survey_id, f"Ошибка разбана {int(context.args[0])}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
        Здравствуй! Я - бот ролевой "Сердца Племён".

        Для того, чтобы вступить в ролевую, прошу тебя сначала ознакомиться с каналом - https://t.me/infoheartsoftheclan
        В нем ты найдешь шаблон анкеты, правила, описания племен, роли и многое другое! По желанию можешь присоединиться ко флуду заранее.

        Когда закончишь придумывать своего персонажа - отправляй анкету прямо сюда и я ее проверю.

        Если твоя анкета не влазит в одно сообщение, можешь отправить частями!

        Важно! Если к анкете вы хотите приложить картинку или картинки, ПОЖАЛУЙСТА, отправьте их в следующем сообщени.
        Иначе ваше сообщение не дойдет :(

        С нетерпением ждем тебя!"""
    logger.debug(f"Start for {update.effective_chat.id}")
    await context.bot.send_message(update.effective_chat.id, text)


def main() -> None:
    create_tables()
    app = (
        Application.builder().token(os.getenv("TOKEN")).build()
    )  # type: ignore
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("survey", receive_survey))
    app.add_handler(CommandHandler("answer", answer_back))
    app.add_handler(
        MessageHandler(
            filters=(filters.TEXT & (~filters.Chat(int(survey_id)))),
            callback=receive_survey,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & (~filters.Chat(int(survey_id))), image
        )
    )
    app.run_polling()


if __name__ == "__main__":
    main()
