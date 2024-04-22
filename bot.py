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

    context.user_data['risultati'] = risultati
    context.user_data['pagina'] = 0
    mostra_risultati(update, context)

def mostra_risultati(update: Update, context: CallbackContext) -> None:
    pagina = context.user_data['pagina']
    risultati = context.user_data['risultati'][pagina*10:(pagina+1)*10]
    keyboard = [[InlineKeyboardButton(f"{i+1}. {item['titolo']}", callback_data=str(i+pagina*10))] for i, item in enumerate(risultati)]
    if pagina > 0:
        keyboard.append([InlineKeyboardButton("Indietro", callback_data='indietro')])
    if len(context.user_data['risultati']) > (pagina+1)*10:
        keyboard.append([InlineKeyboardButton("Avanti", callback_data='avanti')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Seleziona un risultato:', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data.isdigit():
        index = int(query.data)
        risultati = context.user_data['risultati']
        scelto = risultati[index]
        context.user_data['magnet'] = scelto['magnet']
        query.edit_message_text(f"Magnet:\n```{scelto['magnet']}```", parse_mode='MarkdownV2')
    elif query.data == 'indietro':
        context.user_data['pagina'] -= 1
        mostra_risultati(update, context)
    elif query.data == 'avanti':
        context.user_data['pagina'] += 1
        mostra_risultati(update, context)

def main() -> None:
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
