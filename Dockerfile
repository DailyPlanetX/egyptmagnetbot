FROM python:3.9-slim-buster

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir python-telegram-bot==21.1.1 requests

CMD [ "python", "./bot.py" ]
