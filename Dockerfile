FROM kenhv/mirrorbot:ubuntu

WORKDIR /usr/src/app
COPY . .

RUN set -ex \
    && chmod 777 /usr/src/app \
    && apt-get update \
    && apt-get install -y wget \
    && cp netrc /root/.netrc \
    && cp extract pextract /usr/local/bin \
    && chmod +x aria.sh /usr/local/bin/extract /usr/local/bin/pextract

CMD ["bash", "start.sh"]
