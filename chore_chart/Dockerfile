FROM ghcr.io/home-assistant/base:3.24

# Let root manage CUPS queues. Avahi only browses: it must never announce names on the LAN.
RUN apk add --no-cache avahi avahi-tools cups cups-client cups-filters dbus font-dejavu python3 \
        py3-defusedxml py3-fonttools py3-pillow py3-pip tzdata \
    && pip install --no-cache-dir --no-deps --break-system-packages fpdf2==2.8.9 \
    && sed -i 's/^SystemGroup .*/SystemGroup root/' /etc/cups/cups-files.conf \
    && sed -i 's/^#disable-publishing=no/disable-publishing=yes/' /etc/avahi/avahi-daemon.conf

COPY app /app
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
