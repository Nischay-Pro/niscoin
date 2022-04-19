ARG BASE=alpine:3.15

FROM ${BASE}

LABEL maintainer="Nischay Mamidi <NischayPro@protonmail.com>"

COPY entrypoint.sh /entrypoint.sh

RUN apk add --no-cache python3 py-pip

COPY . /app

WORKDIR /app

RUN pip3 install gtts python-telegram-bot

VOLUME [ "/app/database" , "/app/config.json" ]

ENTRYPOINT [ "/entrypoint.sh" ]
