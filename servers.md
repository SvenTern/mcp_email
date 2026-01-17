# MCP Servers - Документация

## SSH доступ к серверу

- **IP**: `217.199.253.8`
- **Пользователь**: `root`
- **Пароль**: `a8ibcyC-QwPFer`
- **Подключение**: `sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8`

---

## Email MCP Server (Streamable HTTP)

### Статус
✅ **Развернут и работает**

### Информация
- **Дата развертывания**: 2026-01-16
- **Версия**: 2.0.0
- **Протокол**: MCP 2025-03-26 (Streamable HTTP)
- **Docker контейнер**: `email-mcp-server`
- **Порт**: 3008
- **Директория**: `/opt/email-mcp-server`

### Доступ

| Endpoint | URL |
|----------|-----|
| Health | `https://mcp.svsfinpro.ru/email/health` |
| Info | `https://mcp.svsfinpro.ru/email/` |
| MCP | `https://mcp.svsfinpro.ru/email/mcp` |

### MCP Tools (17 инструментов)

**Account Management:**
- `imap_add_account` - Добавить аккаунт
- `imap_list_accounts` - Список аккаунтов
- `imap_remove_account` - Удалить аккаунт
- `imap_connect` / `imap_disconnect` - Подключение

**Email Operations:**
- `imap_search_emails` - Поиск писем
- `imap_get_email` - Получить письмо
- `imap_get_latest_emails` - Последние письма
- `imap_mark_as_read` / `imap_mark_as_unread` - Статус прочтения
- `imap_delete_email` - Удалить письмо
- `imap_send_email` - Отправить письмо
- `imap_reply_to_email` - Ответить
- `imap_forward_email` - Переслать

**Folder Operations:**
- `imap_list_folders` - Список папок
- `imap_folder_status` - Статус папки
- `imap_get_unread_count` - Непрочитанные

### Claude Desktop Config

```json
{
  "mcpServers": {
    "email": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/email/mcp"]
    }
  }
}
```

### Управление

```bash
# Логи
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker logs -f email-mcp-server'

# Перезапуск
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'cd /opt/email-mcp-server && docker-compose restart'

# Деплой
cd /Users/sergeistetsko/Documents/GitHub/mcp_email && ./deploy.sh
```

### Nginx Configuration

Добавлено в `/etc/nginx/sites-enabled/mcp.svsfinpro.ru`:

```nginx
# Email MCP Server - Streamable HTTP (Protocol 2025-03-26)
location /email/ {
    rewrite ^/email/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:3008;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Mcp-Session-Id $http_mcp_session_id;
    proxy_pass_header Mcp-Session-Id;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization, Mcp-Session-Id" always;
    add_header Access-Control-Expose-Headers "Mcp-Session-Id" always;
}

location = /email/health {
    proxy_pass http://127.0.0.1:3008/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    access_log off;
}
```

### Тестирование

```bash
# Health
curl https://mcp.svsfinpro.ru/email/health

# Initialize (Streamable HTTP)
curl -X POST "https://mcp.svsfinpro.ru/email/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'
```

---

## Bitrix24 MCP Server (Streamable HTTP)

### Статус
✅ **Развернут и работает**

### Информация
- **Дата развертывания**: 2026-01-16
- **Версия**: 1.0.0
- **Протокол**: MCP 2024-11-05 (Streamable HTTP)
- **Docker контейнер**: `bitrix-mcp-server`
- **Порт**: 3009
- **Директория**: `/opt/bitrix-mcp-server`

### Доступ

| Endpoint | URL |
|----------|-----|
| Health | `https://mcp.svsfinpro.ru/bitrix/health` |
| Info | `https://mcp.svsfinpro.ru/bitrix/` |
| MCP | `https://mcp.svsfinpro.ru/bitrix/mcp` |

### MCP Tools (35 инструментов)

**Task CRUD:**
- `bitrix_task_create` - Создать задачу
- `bitrix_task_update` - Обновить задачу
- `bitrix_task_get` - Получить задачу
- `bitrix_task_list` - Список задач
- `bitrix_task_delete` - Удалить задачу
- `bitrix_task_get_fields` - Получить поля задачи

**Task Status:**
- `bitrix_task_complete` - Завершить задачу
- `bitrix_task_renew` - Возобновить задачу
- `bitrix_task_start` - Начать задачу
- `bitrix_task_pause` - Приостановить задачу
- `bitrix_task_defer` - Отложить задачу
- `bitrix_task_approve` - Одобрить задачу
- `bitrix_task_disapprove` - Отклонить задачу
- `bitrix_task_delegate` - Делегировать задачу

**Checklists:**
- `bitrix_checklist_add` - Добавить элемент чеклиста
- `bitrix_checklist_update` - Обновить элемент
- `bitrix_checklist_delete` - Удалить элемент
- `bitrix_checklist_list` - Список элементов
- `bitrix_checklist_complete` - Отметить выполненным
- `bitrix_checklist_renew` - Снять отметку выполнения

**Comments:**
- `bitrix_comment_add` - Добавить комментарий
- `bitrix_comment_update` - Обновить комментарий
- `bitrix_comment_delete` - Удалить комментарий
- `bitrix_comment_list` - Список комментариев

**Time Tracking:**
- `bitrix_time_add` - Добавить затраченное время
- `bitrix_time_update` - Обновить запись времени
- `bitrix_time_delete` - Удалить запись времени
- `bitrix_time_list` - Список записей времени

**Extra:**
- `bitrix_test_connection` - Проверить подключение
- `bitrix_users_get` - Получить пользователей
- `bitrix_task_favorite_add` - Добавить в избранное
- `bitrix_task_favorite_remove` - Убрать из избранного
- `bitrix_task_attach_files` - Прикрепить файлы
- `bitrix_task_history` - История задачи
- `bitrix_task_counters` - Счетчики задач

### Claude Desktop Config

```json
{
  "mcpServers": {
    "bitrix": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/bitrix/mcp"]
    }
  }
}
```

### Управление

```bash
# Логи
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker logs -f bitrix-mcp-server'

# Перезапуск
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'cd /opt/bitrix-mcp-server && docker-compose restart'

# Статус
sshpass -p 'a8ibcyC-QwPFer' ssh root@217.199.253.8 'docker ps | grep bitrix'
```

### Тестирование

```bash
# Health
curl https://mcp.svsfinpro.ru/bitrix/health

# Initialize (Streamable HTTP)
curl -X POST "https://mcp.svsfinpro.ru/bitrix/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}},"id":1}'

# Test connection
curl -X POST "https://mcp.svsfinpro.ru/bitrix/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"bitrix_test_connection","arguments":{}},"id":2}'
```

---

## Архитектура Gateway

```
Client (Claude Desktop / Web)
    ↓ HTTPS
mcp.svsfinpro.ru (443)
    ↓ SNI Routing
Nginx (8443)
    ↓ Path-based routing
    ├─ /email/*   → localhost:3008 (Email MCP)
    ├─ /bitrix/*  → localhost:3009 (Bitrix24 MCP)
    ├─ /its/*     → localhost:3006 (ITS 1C MCP)
    ├─ /youtube/* → localhost:3003 (YouTube Transcript)
    └─ /news/*    → localhost:3005 (News Aggregator)
```
