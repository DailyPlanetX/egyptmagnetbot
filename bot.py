import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Inserisci il titolo che vuoi cercare:')

def echo(update: Update, context: CallbackContext) -> None:
    titolo = update.message.text
    tabelle = ["film", "anime", "serietv"]
    risultati = []
    for tabella in tabelle:
        url = f"https://ilsegretodellepiramidi.pythonanywhere.com/api?table={tabella}&page=1&filtro={titolo}"
        response = requests.get(url)
        data = response.json()
        for item in data['items']:
            risultati.append(item)

    if risultati:
        context.user_data['risultati'] = risultati
        risultati_text = "\n".join([f"{i+1}. {item['titolo']}" for i, item in enumerate(risultati)])
        update.message.reply_text(f'Seleziona un risultato:\n{risultati_text}')
    else:
        update.message.reply_text('Nessun risultato trovato.')

def select(update: Update, context: CallbackContext) -> None:
    index = int(update.message.text) - 1
    risultati = context.user_data['risultati']
    scelto = risultati[index]
    update.message.reply_text(f"Magnet: {scelto['magnet']}")

def main() -> None:
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & ~Filters.regex(r'^\d+$'), echo))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^\d+$'), select))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
