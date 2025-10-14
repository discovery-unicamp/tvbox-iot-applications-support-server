#!/bin/bash
set -e

LOGFILE=/root/setup.log

# Salva o log do setup
exec > >(tee -a "$LOGFILE") 2>&1

# Atualiza o sistema
sudo apt update
sudo apt upgrade -y
echo "✅ sistema atualizado"

# Instala NGINX
sudo apt install -y nginx
echo "🌐 nginx instalado"

# Instala Redis
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install -y redis 
echo "🧊 redis-server instalado"

# Configura Tailscale Funnel
sudo tailscale funnel --bg 443
echo "🔗 tailscale configurado"

# Atualiza configuração NGINX
sudo cp ./config/default_nginx /etc/nginx/sites-available/default
echo "📝 configuração nginx atualizada"

# Copia os Servidores
sudo mkdir -p /root/servers
sudo cp ./bin/totemUpdateServer /root/servers/
sudo cp ./bin/parkingLotServer /root/servers/
sudo cp ./bin/tvboxMonitoring /root/servers/
chmod +x /root/servers/totemUpdateServer
chmod +x /root/servers/parkingLotServer
chmod +x /root/servers/tvboxMonitoring
echo "📦 servidores copiados e tornados executáveis"

# Cria serviço do UpdateServer para o Systemctl 
sudo cp ./service/update-server.service /etc/systemd/system/update-server.service
sudo systemctl enable update-server.service
echo "🔧 update-server.service criado e habilitado"

# Cria serviço do ParkinglotServer para o Systemctl 
sudo cp ./service/parkingLot-server.service /etc/systemd/system/parkingLot-server.service
sudo systemctl enable parkingLot-server.service
echo "🚗 parkingLot-server.service criado e habilitado"

# Cria serviço do TVBoxMonitoring para o Systemctl 
sudo cp ./service/tvbox-monitoring.service /etc/systemd/system/tvbox-monitoring.service
sudo systemctl enable tvbox-monitoring.service
echo "📺 tvbox-monitoring.service criado e habilitado"

# Atualiza serviço do NGINX para Systemctl
sudo mkdir -p /etc/systemd/system/nginx.service.d
sudo cp ./config/nginx.service.conf /etc/systemd/system/nginx.service.d/override.conf
echo "⚡ nginx service override aplicado"

# Reinicia a maquina
echo "🔄 reiniciando a máquina..."
sleep 5
sudo reboot
