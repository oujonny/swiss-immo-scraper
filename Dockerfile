# syntax=docker/dockerfile:1

FROM python:3.10

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install  --no-cache-dir -r requirements.txt
RUN pip install "ptbcontrib[ptb_jobstores_mongodb] @ git+https://github.com/python-telegram-bot/ptbcontrib.git@main"

RUN apt-get update && apt-get install nodejs -y

COPY . .

CMD [ "python", "-m", "app.main" ]
