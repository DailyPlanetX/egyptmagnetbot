import asyncio
import os
import threading
import time
import libtorrent as lt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
from pyrogram import Client
import requests
from telegram import Document

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
DOWNLOAD_DIR = "~/Downloads"  # replace with your download directory

# shared state for the download
download_state = {
    "downloading": False,
    "progress": 0,
    "magnet": None,
    "message": None,
    "status_message": None,
}

def start_download(magnet, message):
    ses = lt.session()
    info = lt.add_magnet_uri(ses, magnet, {"save_path": DOWNLOAD_DIR})
    while not info.is_seed():
        s = info.status()
        download_state["progress"] = s.progress * 100
        download_state["download_rate"] = s.download_rate
        download_state["total_done"] = s.total_done
        time.sleep(1)
    download_state["downloading"] = False
    time.sleep(10)  # allow send_download_status to run a few more times
    message.reply_text("Download completato!")
    threading.Thread(target=send_file, args=(message.chat_id, info.name())).start()

def login(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Carica il tuo file di sessione:')

def handle_document(update: Update, context: CallbackContext) -> None:
    try:
        file = context.bot.getFile(update.message.document.file_id)
        file.download('my_account.session')
        update.message.reply_text('File di sessione caricato con successo!')
    except Exception as e:
        update.message.reply_text(f"Si è verificato un errore durante il caricamento del file di sessione: {e}")

def send_file(chat_id, file_name):
    try:
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        print("Caricamento in corso...")
        with Client("my_account", api_id=API_ID, api_hash=API_HASH, session_name="./my_account") as app:
            app.send_document(chat_id, file_path)
    except Exception as e:
        print(f"Si è verificato un errore durante l'invio del file: {e}")
        
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
    update.message.reply_text('Ecco i risultati della tua ricerca:', reply_markup=reply_markup)

def echo(update: Update, context: CallbackContext) -> None:
    titolo = update.message.text
    tabelle = ["film", "anime", "serietv"]
    risultati = []
    for tabella in tabelle:
        url = f"https://ilsegretodellepiramidi.pythonanywhere.com/api?table={tabella}&page=1&filtro={titolo}"
        try:
            response = requests.get(url)
            if response.status_code == 200 and response.text.strip():  # check if response is valid
                data = response.json()
                for item in data['items']:
                    risultati.append(item)
            else:
                update.message.reply_text('Errore nel recupero dei dati. Riprova più tardi.')
        except requests.exceptions.RequestException as e:
            update.message.reply_text(f"Si è verificato un errore di rete: {e}")

    context.user_data['risultati'] = risultati
    context.user_data['pagina'] = 0
    if risultati:
        risultati_text = "\n".join([f"{i+1}. {risultato['titolo']}" for i, risultato in enumerate(risultati)])
        update.message.reply_text(f"Ecco i risultati della tua ricerca:\n{risultati_text}")
    else:
        update.message.reply_text("Nessun risultato trovato.")

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
            threading.Thread(target=start_download, args=(download_state["magnet"], download_state["message"])).start()
            time.sleep(1)  # delay the start of send_download_status
            threading.Thread(target=send_download_status, args=(context.bot, query.message.chat_id)).start()
        else:
            query.message.reply_text('Un download è già in corso.')
    elif query.data == 'indietro':
        context.user_data['pagina'] -= 1
        mostra_risultati(update, context)
    elif query.data == 'avanti':
        context.user_data['pagina'] += 1
        mostra_risultati(update, context)

def send_download_status(bot, chat_id):
    for _ in range(20):  # run for a fixed number of times
        if download_state["downloading"]:
            progress = download_state.get('progress', 0)  # use get method to avoid KeyError
            download_rate = download_state.get('download_rate', 0) / 1024  # convert to KB/s
            total_done = download_state.get('total_done', 0) / (1024 * 1024)  # convert to MB
            status_text = f"Progresso del download: {progress}%\nVelocità di download: {download_rate:.2f} KB/s\nTotal scaricato: {total_done:.2f} MB"
            if download_state["status_message"]:
                bot.delete_message(chat_id, download_state["status_message"].message_id)
            download_state["status_message"] = bot.send_message(chat_id, status_text)
        time.sleep(5)

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
    dispatcher.add_handler(CommandHandler("login", login))
    dispatcher.add_handler(MessageHandler(Filters.document & ~Filters.command, handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))  # handle text messages
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(InlineQueryHandler(inlinequery))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
