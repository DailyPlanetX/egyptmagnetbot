FROM python:3.10

WORKDIR /app
COPY . /app

RUN pip install python-telegram-bot==21.1.1 requests
RUN pip show python-telegram-bot

CMD ["python", "bot.py"]
