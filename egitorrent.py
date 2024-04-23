import os
import threading
import time
import libtorrent as lt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
import requests
import shutil

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_DIR = "~/Downloads"  # replace with your download directory

# shared state for the download
download_state = {
    "downloading": False,
    "progress": 0,
    "magnet": None,
    "message": None,
    "status_message": None,
    "download_started": threading.Event(),  # add an Event for download started
}

def start_download(magnet, message):
    ses = lt.session()
    info = lt.add_magnet_uri(ses, magnet, {"save_path": DOWNLOAD_DIR})
    download_state["download_started"].set()  # set the Event when download starts
    while not info.is_seed():
        s = info.status()
        download_state["progress"] = s.progress * 100
        download_state["download_rate"] = s.download_rate
        download_state["total_done"] = s.total_done
        time.sleep(1)
    download_state["downloading"] = False
    message.reply_text("Download completato!")
    return info  # return info for use in other threads

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Inserisci il titolo che vuoi cercare:')

def mostra_risultati(update: Update, context: CallbackContext) -> None:
    risultati = context.user_data['risultati']
    pagina = context.user_data['pagina']
    inizio = pagina * 5
    fine = inizio + 5
    keyboard = []
    for i in range(inizio, min(fine, len(risultati))):
        keyboard.append([InlineKeyboardButton(risultati[i]['titolo'], callback_data=str(i))])
    if pagina > 0:
        keyboard.append([InlineKeyboardButton("Indietro", callback_data='indietro')])
    if fine < len(risultati):
        keyboard.append([InlineKeyboardButton("Avanti", callback_data='avanti')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text('Ecco i risultati della tua ricerca:', reply_markup=reply_markup)
    else:
        query = update.callback_query
        query.edit_message_text('Ecco i risultati della tua ricerca:', reply_markup=reply_markup)

def echo(update: Update, context: CallbackContext) -> None:
    titolo = update.message.text
    tabelle = ["film", "anime", "serietv"]
    risultati = []
    for tabella in tabelle:
        url = f"https://ilsegretodellepiramidi.pythonanywhere.com/api?table={tabella}&page=1&filtro={titolo}"
        response = requests.get(url)
        if response.status_code == 200 and response.text.strip():  # check if response is valid
            data = response.json()
            for item in data['items']:
                risultati.append(item)
        else:
            update.message.reply_text('Errore nel recupero dei dati. Riprova più tardi.')

    context.user_data['risultati'] = risultati
    context.user_data['pagina'] = 0
    mostra_risultati(update, context)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data.isdigit():
        index = int(query.data)
        risultati = context.user_data['risultati']
        scelto = risultati[index]
        context.user_data['magnet'] = scelto['magnet']
        query.edit_message_text(f"Magnet:\n```\n{scelto['magnet']}\n```", parse_mode='MarkdownV2')
        keyboard = [[InlineKeyboardButton("Scarica Magnet", callback_data='download')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('Vuoi scaricare il file?', reply_markup=reply_markup)
    elif query.data == 'download':
        if not download_state["downloading"]:
            download_state["downloading"] = True
            download_state["magnet"] = context.user_data['magnet']
            download_state["message"] = query.message
            info = threading.Thread(target=start_download, args=(download_state["magnet"], download_state["message"])).start()  # capture the returned info
            threading.Thread(target=send_download_status, args=(context.bot, query.message.chat_id, info)).start()  # pass info as an argument
        else:
            query.message.reply_text('Un download è già in corso.')
    elif query.data == 'indietro':
        context.user_data['pagina'] -= 1
        mostra_risultati(update, context)
    elif query.data == 'avanti':
        context.user_data['pagina'] += 1
        mostra_risultati(update, context)

def send_download_status(bot, chat_id, info):  # add info as a parameter
    download_state["download_started"].wait()  # wait for the download to start
    while download_state["downloading"]:
        s = info.status()
        progress = s.progress * 100
        download_rate = s.download_rate / 1024  # convert to kb/s
        total_done = s.total_done / (1024 * 1024)  # convert to mb
        total = s.total_wanted / (1024 * 1024)  # convert to mb
        file_name = info.name()
        total, used, free = shutil.disk_usage("/")
        free = free / (1024 * 1024 * 1024)  # convert to gb
        status_text = f"File: {file_name}\nDimensione del file: {total} MB\nProgresso del download: {progress}%\nVelocità di download: {download_rate} kb/s\nTotal scaricato: {total_done} MB\nSpazio disponibile sul disco: {free} GB"
        if download_state["status_message"]:
            bot.delete_message(chat_id, download_state["status_message"].message_id)
        download_state["status_message"] = bot.send_message(chat_id, status_text)
        time.sleep(20)

def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    tabelle = ["film", "anime", "serietv"]
    risultati = []
    for tabella in tabelle:
        url = f"https://ilsegretodellepiramidi.pythonanywhere.com/api?table={tabella}&page=1&filtro={query}"
        response = requests.get(url)
        data = response.json()
        for item in data['items']:
            risultati.append(item)

    results = [
        InlineQueryResultArticle(
            id=str(i),
            title=item['titolo'],
            input_message_content=InputTextMessageContent(item['magnet'])
        ) for i, item in enumerate(risultati)
    ]

    update.inline_query.answer(results)

def main() -> None:
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(InlineQueryHandler(inlinequery))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
