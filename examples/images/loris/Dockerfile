FROM ubuntu:16.04


# Install base Python and uWSGI (web server) dependencies
RUN apt-get update && \
    apt-get install --yes python3 python3-pip uwsgi uwsgi-plugin-python3 && \
    apt-get clean

RUN pip3 install --upgrade pip

# Imaging dependencies.  These libraries don't change much between versions
# of Loris, so we can cache their installation.
RUN apt-get update && \
    apt-get install --yes libffi-dev libjpeg-turbo8-dev libfreetype6-dev zlib1g-dev \
        liblcms2-dev liblcms2-utils libssl-dev libtiff5-dev libwebp-dev && \
    apt-get clean

ENV LORIS_GITHUB_USER loris-imageserver
ENV LORIS_COMMIT 343485d6bd4235d632533f6af3a0b6fd0233284a

# Download and install the Loris code itself
RUN echo "*** Downloading the Loris source code"
RUN apt-get install --yes unzip wget
RUN wget "https://github.com/$LORIS_GITHUB_USER/loris/archive/$LORIS_COMMIT.zip"
RUN unzip "$LORIS_COMMIT.zip"

# Required or setup.py complains
RUN echo "*** Creating Loris user"
RUN useradd -d /var/www/loris -s /sbin/false loris

RUN echo "*** Installing Loris dependencies"
COPY requirements.txt /
RUN pip3 install -r /requirements.txt

RUN echo "*** Installing Loris itself"
RUN cd "loris-$LORIS_COMMIT" && python3 setup.py install

ENV LORIS_CONF_FILE /opt/loris/etc/loris2.conf

COPY loris2.conf /opt/loris/etc/loris2.conf
COPY loris2.wsgi /var/www/loris2/loris2.wsgi
COPY uwsgi.ini /etc/uwsgi

COPY loris /usr/local/lib/python3.5/dist-packages/Loris-2.3.2-py3.5.egg/loris

EXPOSE 8888

CMD ["/usr/bin/uwsgi", "--ini", "/etc/uwsgi/uwsgi.ini"]
