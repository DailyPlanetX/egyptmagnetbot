import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get('PORT', '8443'))

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Inserisci il titolo che vuoi cercare:')

async def echo(update: Update, context: CallbackContext) -> None:
    titolo = update.message.text
    tabelle = ["film", "anime", "serietv"]
    risultati = []
    for tabella in tabelle:
        url = f"https://ilsegretodellepiramidi.pythonanywhere.com/api?table={tabella}&page=1&filtro={titolo}"
        response = await requests.get(url)
        data = response.json()
        for item in data['items']:
            risultati.append(item)

    if risultati:
        keyboard = [[InlineKeyboardButton(f"{i+1}. {item['titolo']}", callback_data=str(i)) for i, item in enumerate(risultati)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Seleziona un risultato:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Nessun risultato trovato.')

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    risultati = context.user_data['risultati']
    scelto = risultati[int(query.data)]
    await query.edit_message_text(text=f"Magnet: {scelto['magnet']}")

async def main() -> None:
    update_queue = asyncio.Queue()
    updater = Updater(TOKEN, update_queue=update_queue)

    updater.dispatcher.add_handler(CommandHandler("start", start))
    updater.dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    await updater.start_polling()

    await updater.idle()

if __name__ == '__main__':
    asyncio.run(main())
