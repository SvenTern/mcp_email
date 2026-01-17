
---

## Email MCP Server (IMAP/SMTP)

### Статус
🔧 **В разработке**

### Информация о развертывании
- **Дата создания**: 2026-01-16
- **Версия**: v1.0.0
- **Docker контейнер**: `email-mcp-server`
- **Внутренний порт**: `8080`
- **Внешний порт**: `3008`
- **Директория на сервере**: `/opt/email-mcp-server`
- **Протокол**: Streamable HTTP + SSE

### Архитектура

**HTTP Wrapper для nikolausm/imap-mcp-server:**
- HTTP/SSE транспорт для удалённого доступа
- STDIO Bridge для связи с Node.js сервером
- AES-256 шифрование учётных данных
- Поддержка нескольких почтовых аккаунтов

### Доступ к серверу

#### Локальный доступ на сервере
- **Health**: `http://localhost:3008/health`
- **Info**: `http://localhost:3008/`
- **SSE**: `http://localhost:3008/sse`
- **MCP**: `http://localhost:3008/mcp`

#### Внешний доступ через Nginx (планируется)
- **Health**: `https://mcp.svsfinpro.ru/email/health`
- **Info**: `https://mcp.svsfinpro.ru/email/`
- **SSE**: `https://mcp.svsfinpro.ru/email/sse` ⭐ **РЕКОМЕНДУЕТСЯ**
- **MCP**: `https://mcp.svsfinpro.ru/email/mcp`

### MCP Tools (17 инструментов)

**Управление аккаунтами:**
1. **imap_add_account** - Добавить почтовый аккаунт
2. **imap_list_accounts** - Список аккаунтов
3. **imap_remove_account** - Удалить аккаунт
4. **imap_connect** - Подключиться к аккаунту
5. **imap_disconnect** - Отключиться

**Работа с письмами:**
6. **imap_search_emails** - Поиск писем
7. **imap_get_email** - Получить письмо
8. **imap_get_latest_emails** - Последние письма
9. **imap_mark_as_read** - Пометить как прочитанное
10. **imap_mark_as_unread** - Пометить как непрочитанное
11. **imap_delete_email** - Удалить письмо

**Отправка писем:**
12. **imap_send_email** - Отправить письмо
13. **imap_reply_to_email** - Ответить на письмо
14. **imap_forward_email** - Переслать письмо

**Папки:**
15. **imap_list_folders** - Список папок
16. **imap_folder_status** - Статус папки
17. **imap_get_unread_count** - Количество непрочитанных

### Конфигурация для Claude Desktop

#### Локально (STDIO - рекомендуется для личного использования)

```json
{
  "mcpServers": {
    "imap-email": {
      "command": "node",
      "args": ["/Users/sergeistetsko/Documents/GitHub/mcp_email/imap-mcp-server/dist/index.js"]
    }
  }
}
```

#### Удалённо через mcp-remote

```json
{
  "mcpServers": {
    "email-remote": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.svsfinpro.ru/email/sse"
      ]
    }
  }
}
```

#### Через Custom Connector (Claude Web)

**Settings > Connectors > Add custom connector**
- **Name**: `Email`
- **Remote MCP server URL**: `https://mcp.svsfinpro.ru/email/sse`

### Управление контейнером

#### Просмотр логов
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker logs -f email-mcp-server'
```

#### Перезапуск
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'cd /opt/email-mcp-server && docker-compose restart'
```

#### Остановка
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'cd /opt/email-mcp-server && docker-compose down'
```

#### Запуск
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'cd /opt/email-mcp-server && docker-compose up -d'
```

#### Обновление (повторное развертывание)
```bash
cd /Users/sergeistetsko/Documents/GitHub/mcp_email
./deploy.sh
```

### Тестирование

#### Health check
```bash
curl https://mcp.svsfinpro.ru/email/health
```

#### Server info
```bash
curl https://mcp.svsfinpro.ru/email/ | jq .
```

#### Список инструментов через MCP
```bash
curl -X POST https://mcp.svsfinpro.ru/email/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Файлы проекта

Все файлы находятся в: `/Users/sergeistetsko/Documents/GitHub/mcp_email/`

- `Dockerfile` - Production Docker образ
- `docker-compose.yml` - Docker Compose конфигурация
- `deploy.sh` - Скрипт автоматического развертывания
- `nginx-mcp-email.conf` - Конфигурация Nginx
- `src/email_mcp_wrapper/` - Python HTTP wrapper
- `imap-mcp-server/` - Node.js IMAP сервер (git clone)

### Технические детали

- **Runtime**: Python 3.12 + Node.js 20
- **Framework**: aiohttp (HTTP server) + nikolausm/imap-mcp-server (IMAP)
- **Encryption**: AES-256 для учётных данных
- **Protocols**:
  - Streamable HTTP (POST /mcp)
  - Server-Sent Events (GET /sse)
  - Legacy SSE (POST /messages)
- **CORS**: Включен для всех источников

### Переменные окружения

```bash
HOST=0.0.0.0                          # Адрес сервера
PORT=8080                              # Порт
IMAP_SERVER_PATH=/app/imap-mcp-server/dist/index.js  # Путь к серверу
LOG_LEVEL=INFO                         # Уровень логирования
```

### Persistent Storage (Docker Volumes)

```yaml
volumes:
  email_accounts:    # Зашифрованные учётные данные почты
  email_data:        # Данные приложения
```

### Настройка почтовых провайдеров

#### Gmail
```
IMAP: imap.gmail.com:993
SMTP: smtp.gmail.com:465
⚠️ Требуется: 2FA + App Password
```

#### Yandex
```
IMAP: imap.yandex.ru:993
SMTP: smtp.yandex.ru:465
⚠️ Требуется: Пароль приложения
```

#### Mail.ru
```
IMAP: imap.mail.ru:993
SMTP: smtp.mail.ru:465
```

#### Outlook/Hotmail
```
IMAP: outlook.office365.com:993
SMTP: smtp.office365.com:587
```

### Безопасность

- ✅ AES-256 шифрование учётных данных
- ✅ App Passwords (не основные пароли)
- ✅ Docker volumes для изоляции
- ✅ HTTPS через nginx gateway
- ⚠️ **НИКОГДА** не храните пароли в коде

### Troubleshooting

#### Контейнер не запускается
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker logs --tail 50 email-mcp-server'
```

#### Проблемы с IMAP подключением
1. Проверьте App Password
2. Убедитесь что IMAP включен в настройках почты
3. Проверьте firewall

#### Проверка статуса
```bash
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker ps | grep email-mcp-server'
```

### Дальнейшие планы

- [ ] Клонировать nikolausm/imap-mcp-server ✅
- [ ] Создать HTTP wrapper ✅
- [ ] Dockerize решение ✅
- [ ] Deploy на 217.199.253.8
- [ ] Добавить в nginx gateway
- [ ] Тестирование
- [ ] Добавить web wizard для настройки аккаунтов
- [ ] OAuth support для Gmail/Outlook

