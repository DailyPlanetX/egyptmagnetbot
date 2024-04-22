FROM python:3.11

WORKDIR /app
COPY . /app

RUN pip install python-telegram-bot==21.1.1 requests

CMD ["python", "bot.py"]
