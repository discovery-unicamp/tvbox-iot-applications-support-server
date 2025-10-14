#!/bin/bash
set -euo pipefail

# lê variáveis do .env
if [[ ! -f .env ]]; then
  echo "❌ Arquivo .env não encontrado."
  exit 1
fi
source .env

# Caminho do arquivo .img
IMG_PATH=${IMG_PATH:-"./image.img"}

# Comando extra opcional pro primeiro boot
CMD_TO_RUN=${CMD_TO_RUN:-"echo 'Nenhum comando extra definido'"}

echo "🔍 Detectando e montando imagem .img..."

# Cria loop device com partições expostas
LOOP_DEV=$(sudo losetup -f --show -P "$IMG_PATH")
if [[ -z "$LOOP_DEV" ]]; then
    echo "❌ Não foi possível criar o dispositivo de loopback."
    exit 1
fi
echo "✅ Dispositivo de loopback criado: $LOOP_DEV"

# Identifica partição única (p1)
ROOT_PART="${LOOP_DEV}p1"

# Cria ponto de montagem temporário
ROOT_MNT=$(mktemp -d)

echo "📂 Montando partição..."
sudo mount "$ROOT_PART" "$ROOT_MNT"

echo "📝 Escrevendo arquivos de configuração..."

sudo mkdir -p "$ROOT_MNT/etc/systemd/system/getty@tty1.service.d"
cat <<EOF | sudo tee "$ROOT_MNT/etc/systemd/system/getty@tty1.service.d/override.conf" > /dev/null
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I \$TERM
Type=simple
EOF
echo "✔ Escrito $ROOT_MNT/etc/systemd/system/getty@tty1.service.d/override.conf."

# --- .not_logged_in_yet ---
mkdir -p "$ROOT_MNT/root"
cat > "$ROOT_MNT/root/.not_logged_in_yet" <<EOF
PRESET_NET_CHANGE_DEFAULTS="1"
PRESET_NET_ETHERNET_ENABLED="0"

PRESET_NET_WIFI_ENABLED="1"
PRESET_NET_WIFI_SSID="${WIFI_SSID}"
PRESET_NET_WIFI_KEY="${WIFI_PASS}"
PRESET_NET_WIFI_COUNTRYCODE="${WIFI_COUNTRYCODE}"
PRESET_CONNECT_WIRELESS="n"
PRESET_NET_USE_STATIC="0"

SET_LANG_BASED_ON_LOCATION="y"
PRESET_LOCALE="${LOCALE}"
PRESET_TIMEZONE="${TIMEZONE}"

PRESET_ROOT_PASSWORD="${ROOT_PASS}"
PRESET_ROOT_KEY=""

PRESET_USER_NAME="${USER_NAME}"
PRESET_USER_PASSWORD="${USER_PASS}"
PRESET_USER_KEY=""
PRESET_DEFAULT_REALNAME="${USER_REAL_NAME}"
PRESET_USER_SHELL="bash"
EOF
chmod 600 "$ROOT_MNT/root/.not_logged_in_yet"
echo "✔ Escrito $ROOT_MNT/root/.not_logged_in_yet"

# --- provisioning.sh ---
cat > "$ROOT_MNT/root/provisioning.sh" <<EOF
#!/bin/bash
set -e
echo "Provisioning started"
eval "${CMD_TO_RUN}"
echo "Provisioning complete"
EOF
chmod +x "$ROOT_MNT/root/provisioning.sh"
echo "✔ Escrito $ROOT_MNT/root/provisioning.sh"

# Desmonta e limpa
sync
sudo umount "$ROOT_MNT"
rm -rf "$ROOT_MNT"
sudo losetup -d "$LOOP_DEV"

echo "🎉 Configuração concluída."
