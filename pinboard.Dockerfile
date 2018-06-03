FROM alpine

RUN apk add --update gcc libxml2-dev libxslt-dev musl-dev python3 python3-dev

COPY requirements.txt /
RUN pip3 install -r /requirements.txt

RUN apk add git

COPY . /app
WORKDIR /app

EXPOSE 5000

