# Настройка прокси для обхода региональных ограничений

## Проблема

Anthropic Claude API блокирует запросы из России (HTTP 403 Forbidden). Для работы AI-оптимизации (ранжирование результатов поиска и экстракция контента) необходимо использовать прокси.

## Решение

Используется Mihomo (современная версия Clash) с Trojan Reality прокси-сервером через svsproxy.xyz.

## Компоненты

### 1. Mihomo Proxy Server

**Установка:**
```bash
# Скачать mihomo для linux-amd64
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.18.10/mihomo-linux-amd64-v1.18.10.gz
gunzip mihomo-linux-amd64-v1.18.10.gz
chmod +x mihomo-linux-amd64-v1.18.10
sudo mv mihomo-linux-amd64-v1.18.10 /usr/local/bin/mihomo
```

**Конфигурация:**
- Файл: `/etc/mihomo/config.yaml` (см. proxy.md)
- Mixed-port: 7897 (HTTP + SOCKS5)
- Режим: Rule-based routing
- Прокси: Trojan Reality svsproxy.xyz:443

**Systemd service:**
```bash
sudo nano /etc/systemd/system/mihomo.service
```

```ini
[Unit]
Description=Mihomo Proxy Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mihomo -d /etc/mihomo
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Запуск:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mihomo
sudo systemctl start mihomo
sudo systemctl status mihomo
```

**Проверка:**
```bash
# Проверить, что прокси слушает на 7897
netstat -tuln | grep 7897
# или
ss -tuln | grep 7897
```

### 2. Claude Client с поддержкой прокси

**Изменения в src/its_1c_mcp/claude_client.py:**

```python
# Proxy configuration (optional)
proxy_url = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

# Build mounts for proxy support
mounts = None
if proxy_url:
    # httpx requires explicit proxy configuration for AsyncClient
    mounts = {
        "http://": httpx.AsyncHTTPTransport(proxy=proxy_url),
        "https://": httpx.AsyncHTTPTransport(proxy=proxy_url),
    }
    logger.info(f"Using proxy for Claude API: {proxy_url}")

self.client = httpx.AsyncClient(
    timeout=httpx.Timeout(self.timeout),
    headers={
        "anthropic-version": "2023-06-01",
        "x-api-key": self.api_key,
        "content-type": "application/json",
    },
    mounts=mounts,  # ← Добавлено для прокси
)
```

### 3. Docker Configuration

**docker-compose.yml:**

```yaml
services:
  its-mcp-oauth:
    build: .
    container_name: its-1c-mcp-oauth
    # Use host network to access Mihomo proxy on localhost:7897
    network_mode: host  # ← Обязательно для доступа к localhost:7897
    environment:
      - HTTP_PROXY=${HTTP_PROXY:-}
      - HTTPS_PROXY=${HTTPS_PROXY:-}
      # ... остальные переменные
```

**.env файл:**

```bash
# Claude API Configuration
ANTHROPIC_API_KEY=sk-ant-api03-...

# Claude Model Selection
CLAUDE_MODEL=claude-3-haiku-20240307

# HTTP Proxy Configuration (для обхода региональных ограничений)
HTTP_PROXY=http://localhost:7897
HTTPS_PROXY=http://localhost:7897
```

## Deployment

```bash
cd /opt/its-1c-mcp-oauth

# Обновить код
git pull  # или скопировать файлы вручную

# Пересобрать и запустить
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Проверить логи
docker logs -f its-1c-mcp-oauth
```

## Проверка работоспособности

### 1. Проверить прокси

```bash
# Из хоста
curl -x http://localhost:7897 https://api.anthropic.com/v1/messages -I

# Из контейнера
docker exec its-1c-mcp-oauth python3 -c "
import httpx
response = httpx.get('https://api.anthropic.com/v1/messages',
    proxies={'https://': 'http://localhost:7897'})
print(f'Status: {response.status_code}')
"
```

### 2. Проверить Claude API

```bash
docker exec its-1c-mcp-oauth python3 -c "
import asyncio
import os
import sys

os.environ['HTTP_PROXY'] = 'http://localhost:7897'
sys.path.insert(0, '/app/src')

async def test():
    from its_1c_mcp.claude_client import ClaudeClient
    client = ClaudeClient()
    result = await client._call_api(
        [{'role': 'user', 'content': 'Hello'}],
        max_tokens=20
    )
    print(f'✅ SUCCESS: {result}')
    await client.close()

asyncio.run(test())
"
```

### 3. Проверить логи

```bash
# Должно быть в логах:
docker logs its-1c-mcp-oauth 2>&1 | grep -i proxy

# Ожидаемый вывод:
# Using proxy for Claude API: http://localhost:7897
```

## Troubleshooting

### Прокси не запущен

```bash
sudo systemctl status mihomo
sudo systemctl restart mihomo
sudo journalctl -u mihomo -f
```

### Docker не видит localhost

Убедитесь, что используется `network_mode: host` в docker-compose.yml.

### 403 Forbidden всё равно

1. Проверить, что Mihomo работает: `ss -tuln | grep 7897`
2. Проверить правила в `/etc/mihomo/config.yaml`
3. Проверить логи Mihomo: `sudo journalctl -u mihomo -n 100`

### API ключ не работает

Обновить `ANTHROPIC_API_KEY` в `.env` файле:
```bash
nano /opt/its-1c-mcp-oauth/.env
# Раскомментировать и обновить ключ
docker-compose restart
```

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│  MCP ITS Server (Docker)                            │
│  ┌────────────────────────────────────────────┐     │
│  │  ClaudeClient                              │     │
│  │  ├─ HTTP_PROXY=http://localhost:7897       │     │
│  │  └─ AsyncHTTPTransport(proxy=...)          │     │
│  └────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
                       ↓
            ┌──────────────────────┐
            │  Mihomo Proxy        │
            │  localhost:7897      │
            └──────────────────────┘
                       ↓
            ┌──────────────────────┐
            │  svsproxy.xyz:443    │
            │  Trojan Reality      │
            └──────────────────────┘
                       ↓
            ┌──────────────────────┐
            │  api.anthropic.com   │
            │  Claude API          │
            └──────────────────────┘
```

## Результаты

- ✅ Claude API доступен из России через прокси
- ✅ AI-ранжирование результатов поиска работает
- ✅ AI-экстракция релевантного контента работает
- ✅ Автоматический запуск Mihomo через systemd
- ✅ Persistent настройки через docker-compose
