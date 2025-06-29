import os
from typing import Literal, TypedDict, cast, List

from telegram import (
    Update,
    Message,
    InputMediaVideo,
    InputMediaPhoto,
    InputMediaDocument,
    InputMediaAudio,
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

load_dotenv()
group_id = os.getenv('CHAT')
survey_id = os.getenv('CHAT_SURVEYS')


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


async def send_survey_photo(photo, caption: str, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(survey_id, photo, caption)


async def send_survey_media_group(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    context.job.data = cast(List[MsgDict], context.job.data)
    media = []
    command = False
    sender = context.job.data[0].get('sender_id')
    for msg_dict in context.job.data:
        if msg_dict["caption"] and "/survey" in msg_dict["caption"]:
            command = True
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
    if not command:
        return
    if len(media) > 3 and sender:
        await bot.send_message(
            sender,
            "К анкете можно прикрепить не более 3 фото! Пожалуйста, отправьте анкету еще раз.",
        )
    else:
        await bot.send_media_group(survey_id, media)
        await reply(bot, sender)


async def receive_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = edit_text(update.message.text, update.effective_chat.id)
    await send_survey(text, context)
    await reply(context.bot, update.effective_chat.id)


async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: Message = update.effective_message
    if not message.media_group_id:
        text = update.message.caption
        if "/survey" in text:
            text = edit_text(text or "", update.effective_chat.id)
            photo = update.message.photo[-1]
            await send_survey_photo(photo, text, context)
            await reply(context.bot, update.effective_chat.id)
    elif message.photo and message.media_group_id:
        media_type = effective_message_type(message)
        media_id = message.photo[-1].file_id
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
        Здравствуй! Я - бот ролевой "Сердца Племён".

        Для того, чтобы вступить в ролевую, прошу тебя сначала ознакомиться с каналом - https://t.me/infoheartsoftheclan
        В нем ты найдешь шаблон анкеты, правила, описания племен, роли и многое другое! По желанию можешь присоединиться ко флуду заранее.

        Когда закончишь придумывать своего персонажа - отправляй анкету прямо сюда и я ее проверю.

        Для отправки анкеты используй команду /survey [текст анкеты]!

        Если твоя анкета не влазит в одно сообщение, можешь отправить частями - но каждое новое тоже нужно начинать с /survey!

        С нетерпением ждем тебя!"""
    await context.bot.send_message(update.effective_chat.id, text)


def main() -> None:
    app = (
        Application.builder().token(os.getenv("TOKEN")).concurrent_updates(True).build()
    )  # type: ignore
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("survey", receive_survey))
    app.add_handler(CommandHandler("answer", answer_back))
    app.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & (~filters.Chat(int(survey_id))), image
        )
    )
    app.run_polling()


if __name__ == '__main__':
    main()
