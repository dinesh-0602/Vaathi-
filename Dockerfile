FROM kenhv/mirrorbot:ubuntu

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY extract /usr/local/bin
COPY pextract /usr/local/bin
RUN chmod +x /usr/local/bin/extract && chmod +x /usr/local/bin/pextract

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
COPY .netrc /root/.netrc
RUN chmod 600 /usr/src/app/.netrc
RUN chmod +x aria.sh

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

RUN set -ex \
    && chmod 777 /usr/src/app \
    && apt-get update \
    && apt-get install -y wget \
    && cp .netrc /root/.netrc \
    && cp extract pextract /usr/local/bin \
    && chmod +x aria.sh /usr/local/bin/extract /usr/local/bin/pextract

CMD ["bash", "start.sh"]
