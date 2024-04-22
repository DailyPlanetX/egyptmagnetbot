FROM python:3.10

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
RUN pip show python-telegram-bot

CMD ["python", "bot.py"]
