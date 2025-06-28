import os

from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler
from dotenv import load_dotenv

load_dotenv()
group_id = os.getenv('CHAT')
survey_id = os.getenv('CHAT_SURVEYS')


async def answer_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(survey_id):
        return
    full_text: str = update.message.text.replace('/answer', '')
    chat_id, reply_text = full_text.strip().split('\n', 1)
    print(chat_id)
    await context.bot.send_message(chat_id, reply_text)


async def send_survey(message: str, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(survey_id, message)


async def receive_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text.replace('/survey', '')
    reply_text = 'Спасибо за заявку! Ваша анкета была направлена админинстраторам на проверку.'
    text = f'Sender chat id: {update.effective_chat.id}\n\n' + text + '\n#анкета'
    await send_survey(text, context)
    await context.bot.send_message(update.effective_chat.id, reply_text)


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
    app = Application.builder().token(os.getenv('TOKEN')).concurrent_updates(True).build() # type: ignore
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('survey', receive_survey))
    app.add_handler(CommandHandler('answer', answer_back))
    app.run_polling()


if __name__ == '__main__':
    main()
