#!/command/with-contenv bashio
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
    export PORT="$(bashio::app.ingress_port)"
fi
mkdir -p /run/dbus
dbus-daemon --system
avahi-daemon --daemonize --no-chroot
cupsd
exec python3 /app/server.py
