import asyncio
import os
import threading
import time
import libtorrent as lt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
import requests
from telegram import Document
import logging
import sys
from telethon.sync import TelegramClient
from telethon.tl.types import InputPeerUser, InputPeerChannel
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from time import sleep
import traceback
import random
from io import StringIO

# Configura il logging per scrivere i log sulla console e su un file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")])

# Ora puoi utilizzare logging.info(), logging.warning(), ecc. per scrivere i log
logging.info("Inizio caricamento...")

# La tua nuova funzione progress
def progress(current, total):
    logging.info("Caricato: {0:.1f}%".format(current * 100 / total))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
CHAT = os.getenv("CHAT")
DOWNLOAD_DIR = "/root/Downloads"  # replace with your download directory

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
    document = update.message.document
    if document:
        file = context.bot.get_file(document.file_id)
        file.download(custom_path="my_account.session")
        update.message.reply_text('File di sessione caricato con successo.')

def carica(update: Update, context: CallbackContext) -> None:
    session_file = 'my_account.session'
    if not os.path.exists(session_file):
        update.message.reply_text('Il file di sessione non esiste. Per favore, caricalo.')
        return

    download_dir = '/root/Downloads'  # Docker download directory
    if not os.path.exists(download_dir):
        update.message.reply_text('La directory di download non esiste.')
        return

    files = os.listdir(download_dir)  # consider all files
    if not files:
        update.message.reply_text('Non ci sono file da caricare.')
        return

    context.user_data['files'] = files  # store all files in user_data
    keyboard = [[InlineKeyboardButton(f, callback_data=f)] for f in files]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Quale file vuoi caricare?', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if 'files' in context.user_data and query.data in context.user_data['files']:
        file = query.data
        file_path = os.path.join('/root/Downloads', file)
        if not os.path.exists(file_path):
            query.edit_message_text(f'Il file {file} non esiste.')
            return
        asyncio.set_event_loop(asyncio.new_event_loop())
        with TelegramClient(file_path.replace('.session', ''), API_ID, API_HASH) as client:
            client.send_file(CHAT, file_path, progress_callback=progress)
            query.edit_message_text(f'File {file} caricato con successo.')
    elif query.data.isdigit():
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
    elif query.data == 's' or query.data == 'n':
        file = context.user_data['current_file']
        if query.data == 's':
            file_path = os.path.join(DOWNLOAD_DIR, file)
            if not os.path.exists(file_path):
                query.edit_message_text(f'Il file {file} non esiste.')
                return
            if file == 'my_account.session':
                with TelegramClient("my_account", API_ID, API_HASH) as client:
                    client.send_file(update.message.chat_id, file_path, progress_callback=progress)
                    query.edit_message_text(f'File {file} caricato con successo.')
            else:
                query.edit_message_text(f'Il file {file} non è un file di sessione valido.')
        elif query.data == 'n':
            query.edit_message_text('File non caricato.')
            
def handle_document(update: Update, context: CallbackContext) -> None:
    try:
        file = context.bot.getFile(update.message.document.file_id)
        file.download(os.path.join(DOWNLOAD_DIR, 'my_account.session'))  # download the file to the correct directory
        update.message.reply_text('File di sessione caricato con successo!')
        # Una volta che il file è stato caricato con successo, chiamiamo la funzione carica
        carica(update, context)
    except Exception as e:
        update.message.reply_text(f"Si è verificato un errore durante il caricamento del file di sessione: {e}")

def send_file(chat_id, file_name):
    try:
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        print("Inizio caricamento...")
        start_time = time.time()
        with TelegramClient("my_account", API_ID, API_HASH) as client:
            client.send_file(chat_id, file_path, progress_callback=progress)
            time.sleep(1)  # Aggiungi una pausa di 1 secondo tra ogni iterazione
        end_time = time.time()
        print(f"\nFile caricato con successo.")
        print(f"Tempo impiegato per il caricamento: {end_time - start_time} secondi")
    except TimeoutError:
        print("Il caricamento del file ha impiegato troppo tempo.")
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
        mostra_risultati(update, context)  # call mostra_risultati directly
    else:
        update.message.reply_text("Nessun risultato trovato.")

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

def main() -> None:
    updater = Updater(token=TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("login", login))
    dispatcher.add_handler(CommandHandler("caricamento", carica))
    dispatcher.add_handler(MessageHandler(Filters.document & ~Filters.command, handle_document))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))  # handle text messages
    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
