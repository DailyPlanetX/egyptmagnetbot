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
        keyboard = [[InlineKeyboardButton(f"{i+1}. {item['titolo']}", callback_data=str(i))] for i, item in enumerate(risultati)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Seleziona un risultato:', reply_markup=reply_markup)
    else:
        update.message.reply_text('Nessun risultato trovato.')

def select(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    index = int(query.data)
    risultati = context.user_data['risultati']
    scelto = risultati[index]
    context.user_data['magnet'] = scelto['magnet']
    keyboard = [[InlineKeyboardButton("Copia Magnet", callback_data='copia_magnet')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('Premi il pulsante per copiare il magnet:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'copia_magnet':
        magnet = context.user_data['magnet']
        query.edit_message_text(f"Magnet: {magnet}")

def main() -> None:
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & ~Filters.regex(r'^\d+$'), echo))
    dispatcher.add_handler(CallbackQueryHandler(select, pattern='^\d+$'))
    dispatcher.add_handler(CallbackQueryHandler(button, pattern='^copia_magnet$'))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
