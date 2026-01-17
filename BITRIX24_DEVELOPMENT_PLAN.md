# Bitrix24 Tasks MCP Server - План разработки

## 📋 Обзор

Создание отдельного MCP-сервера для работы с задачами Bitrix24 через REST API.
Сервер будет работать в отдельном Docker-контейнере, независимо от Email MCP Server.

**Портал:** `portal.nortex.ru`
**Webhook URL:** `https://portal.nortex.ru/rest/1/ab2pds4xqqph27fw/`

---

## 🏗️ Архитектура

### Multi-Container Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          MCP Gateway (nginx)                                │
│                        mcp.svsfinpro.ru                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│     /email/*              /bitrix/*              /other/*                  │
│         │                     │                      │                      │
│         ▼                     ▼                      ▼                      │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│  │ email-mcp   │      │ bitrix-mcp  │      │ other-mcp   │                │
│  │ :3008       │      │ :3009       │      │ :30xx       │                │
│  └─────────────┘      └─────────────┘      └─────────────┘                │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Bitrix24 MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   bitrix-mcp-server Container                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐       ┌──────────────────────────┐         │
│  │ STDIO Transport │       │ Streamable HTTP Transport │         │
│  │ (Claude Desktop)│       │ (Claude Web / Remote)     │         │
│  └────────┬────────┘       └────────────┬─────────────┘         │
│           │                             │                        │
│           └──────────┬──────────────────┘                        │
│                      ▼                                           │
│           ┌─────────────────────┐                               │
│           │   MCP Tool Handler  │                               │
│           │  (bitrix-mcp-server)│                               │
│           └────────┬────────────┘                               │
│                    ▼                                             │
│           ┌─────────────────────┐                               │
│           │  Bitrix24 Service   │                               │
│           │  (HTTP REST Client) │                               │
│           └────────┬────────────┘                               │
│                    ▼                                             │
│           ┌─────────────────────┐                               │
│           │  Bitrix24 REST API  │                               │
│           │  portal.nortex.ru   │                               │
│           └─────────────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Структура проекта

```
mcp_email/
├── imap-mcp-server/              # Существующий Email MCP Server
│   ├── src/
│   ├── package.json
│   └── Dockerfile
│
├── bitrix-mcp-server/            # НОВЫЙ: Bitrix24 MCP Server
│   ├── src/
│   │   ├── index.ts              # Entry point
│   │   ├── services/
│   │   │   └── bitrix-service.ts # HTTP client для Bitrix24 API
│   │   ├── tools/
│   │   │   ├── index.ts          # Tool registration hub
│   │   │   ├── task-tools.ts     # CRUD задач
│   │   │   ├── status-tools.ts   # Управление статусами
│   │   │   ├── checklist-tools.ts# Чеклисты
│   │   │   ├── comment-tools.ts  # Комментарии
│   │   │   └── time-tools.ts     # Учёт времени
│   │   └── types/
│   │       └── bitrix.ts         # TypeScript интерфейсы
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
│
├── src/
│   ├── email_mcp_wrapper/        # Python wrapper для Email
│   └── bitrix_mcp_wrapper/       # НОВЫЙ: Python wrapper для Bitrix24
│       ├── __init__.py
│       ├── http_server.py
│       └── stdio_bridge.py
│
├── docker-compose.yml            # Обновить: добавить bitrix-mcp
├── nginx-mcp-bitrix.conf         # НОВЫЙ: nginx config для Bitrix
└── BITRIX24_DEVELOPMENT_PLAN.md  # Этот файл
```

---

## 🔧 Bitrix24 REST API Methods

### Основные методы задач (`tasks.task.*`)

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `tasks.task.add` | Создать задачу | `bitrix_task_create` |
| `tasks.task.update` | Обновить задачу | `bitrix_task_update` |
| `tasks.task.get` | Получить задачу | `bitrix_task_get` |
| `tasks.task.list` | Список задач | `bitrix_task_list` |
| `tasks.task.delete` | Удалить задачу | `bitrix_task_delete` |
| `tasks.task.getFields` | Получить поля | `bitrix_task_get_fields` |

### Управление статусом

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `tasks.task.complete` | Завершить | `bitrix_task_complete` |
| `tasks.task.renew` | Возобновить | `bitrix_task_renew` |
| `tasks.task.start` | Начать | `bitrix_task_start` |
| `tasks.task.pause` | Приостановить | `bitrix_task_pause` |
| `tasks.task.defer` | Отложить | `bitrix_task_defer` |
| `tasks.task.approve` | Принять | `bitrix_task_approve` |
| `tasks.task.disapprove` | Отклонить | `bitrix_task_disapprove` |
| `tasks.task.delegate` | Делегировать | `bitrix_task_delegate` |

### Чеклисты (`task.checklistitem.*`)

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `task.checklistitem.add` | Добавить пункт | `bitrix_checklist_add` |
| `task.checklistitem.update` | Обновить пункт | `bitrix_checklist_update` |
| `task.checklistitem.delete` | Удалить пункт | `bitrix_checklist_delete` |
| `task.checklistitem.getlist` | Список пунктов | `bitrix_checklist_list` |
| `task.checklistitem.complete` | Выполнить | `bitrix_checklist_complete` |
| `task.checklistitem.renew` | Снять выполнение | `bitrix_checklist_renew` |

### Комментарии (`task.commentitem.*`)

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `task.commentitem.add` | Добавить | `bitrix_comment_add` |
| `task.commentitem.update` | Обновить | `bitrix_comment_update` |
| `task.commentitem.delete` | Удалить | `bitrix_comment_delete` |
| `task.commentitem.getlist` | Список | `bitrix_comment_list` |

### Учёт времени (`task.elapseditem.*`)

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `task.elapseditem.add` | Добавить запись | `bitrix_time_add` |
| `task.elapseditem.update` | Обновить | `bitrix_time_update` |
| `task.elapseditem.delete` | Удалить | `bitrix_time_delete` |
| `task.elapseditem.getlist` | Список | `bitrix_time_list` |

### Дополнительные методы

| Метод | Описание | Tool Name |
|-------|----------|-----------|
| `tasks.task.favorite.add` | В избранное | `bitrix_task_favorite_add` |
| `tasks.task.favorite.remove` | Из избранного | `bitrix_task_favorite_remove` |
| `tasks.task.files.attach` | Прикрепить файлы | `bitrix_task_attach_files` |
| `tasks.task.history.list` | История | `bitrix_task_history` |
| `tasks.task.counters.get` | Счётчики | `bitrix_task_counters` |
| `user.get` | Получить пользователей | `bitrix_users_get` |

---

## 📋 Поля задачи Bitrix24

### Обязательные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `TITLE` | string | Заголовок задачи |
| `RESPONSIBLE_ID` | integer | ID исполнителя |

### Основные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `DESCRIPTION` | string | Описание задачи |
| `CREATED_BY` | integer | ID постановщика |
| `ACCOMPLICES` | array[int] | Соисполнители |
| `AUDITORS` | array[int] | Наблюдатели |
| `DEADLINE` | datetime | Крайний срок |
| `START_DATE_PLAN` | datetime | Плановое начало |
| `END_DATE_PLAN` | datetime | Плановое окончание |
| `PRIORITY` | integer | 0=обычный, 2=высокий |
| `GROUP_ID` | integer | ID проекта/группы |
| `PARENT_ID` | integer | ID родительской задачи |
| `TAGS` | array[string] | Теги |
| `TIME_ESTIMATE` | integer | Плановое время (секунды) |
| `ALLOW_CHANGE_DEADLINE` | Y/N | Разрешить менять дедлайн |
| `TASK_CONTROL` | Y/N | Требуется принять работу |
| `ADD_IN_REPORT` | Y/N | Включить в отчёт |
| `ALLOW_TIME_TRACKING` | Y/N | Учёт времени |
| `UF_CRM_TASK` | array | Привязка к CRM |

---

## 🛠️ Этапы разработки

### Этап 1: Инициализация проекта ✅
- [x] Создать директорию `bitrix-mcp-server/`
- [x] Инициализировать package.json
- [x] Настроить TypeScript (tsconfig.json)
- [x] Установить зависимости (MCP SDK, zod, axios)

### Этап 2: Создание сервиса Bitrix24 ✅
- [x] Создать `bitrix-service.ts` - HTTP клиент
- [x] Реализовать методы для REST API
- [x] Добавить обработку ошибок
- [x] Добавить логирование

### Этап 3: Реализация Tools - Задачи ✅
- [x] `bitrix_task_create` - создание задачи
- [x] `bitrix_task_update` - обновление
- [x] `bitrix_task_get` - получение
- [x] `bitrix_task_list` - список с фильтрами
- [x] `bitrix_task_delete` - удаление
- [x] `bitrix_task_get_fields` - получение полей

### Этап 4: Реализация Tools - Статусы ✅
- [x] `bitrix_task_complete` - завершить
- [x] `bitrix_task_renew` - возобновить
- [x] `bitrix_task_start` - начать
- [x] `bitrix_task_pause` - приостановить
- [x] `bitrix_task_defer` - отложить
- [x] `bitrix_task_approve` - принять
- [x] `bitrix_task_disapprove` - отклонить
- [x] `bitrix_task_delegate` - делегировать

### Этап 5: Реализация Tools - Чеклисты ✅
- [x] `bitrix_checklist_add`
- [x] `bitrix_checklist_update`
- [x] `bitrix_checklist_delete`
- [x] `bitrix_checklist_list`
- [x] `bitrix_checklist_complete`
- [x] `bitrix_checklist_renew`

### Этап 6: Реализация Tools - Комментарии ✅
- [x] `bitrix_comment_add`
- [x] `bitrix_comment_update`
- [x] `bitrix_comment_delete`
- [x] `bitrix_comment_list`

### Этап 7: Реализация Tools - Учёт времени ✅
- [x] `bitrix_time_add`
- [x] `bitrix_time_update`
- [x] `bitrix_time_delete`
- [x] `bitrix_time_list`

### Этап 8: Дополнительные Tools ✅
- [x] `bitrix_task_favorite_add/remove`
- [x] `bitrix_task_attach_files`
- [x] `bitrix_task_history`
- [x] `bitrix_task_counters`
- [x] `bitrix_users_get`

### Этап 9: HTTP Wrapper ✅
- [x] Создать `bitrix_mcp_wrapper/` Python модуль
- [x] Реализовать Streamable HTTP transport
- [x] Добавить health check endpoint

### Этап 10: Docker & Deployment ✅
- [x] Создать Dockerfile для bitrix-mcp-server
- [x] Обновить docker-compose.yml
- [x] Создать nginx конфигурацию
- [ ] Деплой на сервер (требует доступ к серверу)

---

## 🔐 Конфигурация

### Environment Variables

```bash
# .env файл
BITRIX24_WEBHOOK_URL=https://portal.nortex.ru/rest/1/ab2pds4xqqph27fw/

# Опционально
BITRIX24_LOG_LEVEL=INFO
BITRIX24_TIMEOUT=30000
```

### Docker Compose (обновление)

```yaml
services:
  # Существующий email-mcp
  email-mcp:
    # ... existing config ...
    ports:
      - "3008:8080"

  # НОВЫЙ: bitrix-mcp
  bitrix-mcp:
    build:
      context: ./bitrix-mcp-server
      dockerfile: Dockerfile
    image: bitrix-mcp-server:latest
    container_name: bitrix-mcp-server
    ports:
      - "3009:8080"
    environment:
      - HOST=0.0.0.0
      - PORT=8080
      - BITRIX24_WEBHOOK_URL=${BITRIX24_WEBHOOK_URL}
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/mcp-bitrix

location /bitrix/ {
    proxy_pass http://localhost:3009/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400;
}
```

---

## 📊 Полный список Tools (34 инструмента)

### Конфигурация (2)
1. `bitrix_test_connection` - Проверить подключение
2. `bitrix_users_get` - Получить пользователей

### Задачи CRUD (6)
3. `bitrix_task_create` - Создать задачу
4. `bitrix_task_update` - Обновить задачу
5. `bitrix_task_get` - Получить задачу
6. `bitrix_task_list` - Список задач
7. `bitrix_task_delete` - Удалить задачу
8. `bitrix_task_get_fields` - Получить поля

### Статусы задач (8)
9. `bitrix_task_complete` - Завершить
10. `bitrix_task_renew` - Возобновить
11. `bitrix_task_start` - Начать
12. `bitrix_task_pause` - Приостановить
13. `bitrix_task_defer` - Отложить
14. `bitrix_task_approve` - Принять работу
15. `bitrix_task_disapprove` - Отклонить работу
16. `bitrix_task_delegate` - Делегировать

### Чеклисты (6)
17. `bitrix_checklist_add` - Добавить пункт
18. `bitrix_checklist_update` - Обновить пункт
19. `bitrix_checklist_delete` - Удалить пункт
20. `bitrix_checklist_list` - Список пунктов
21. `bitrix_checklist_complete` - Отметить выполненным
22. `bitrix_checklist_renew` - Снять выполнение

### Комментарии (4)
23. `bitrix_comment_add` - Добавить
24. `bitrix_comment_update` - Обновить
25. `bitrix_comment_delete` - Удалить
26. `bitrix_comment_list` - Список

### Учёт времени (4)
27. `bitrix_time_add` - Добавить запись
28. `bitrix_time_update` - Обновить
29. `bitrix_time_delete` - Удалить
30. `bitrix_time_list` - Список

### Дополнительные (4)
31. `bitrix_task_favorite_add` - В избранное
32. `bitrix_task_favorite_remove` - Из избранного
33. `bitrix_task_attach_files` - Прикрепить файлы
34. `bitrix_task_history` - История изменений

---

## 📚 Ссылки на документацию

- [Tasks API Overview](https://apidocs.bitrix24.com/api-reference/tasks/index.html)
- [tasks.task.add](https://apidocs.bitrix24.com/api-reference/tasks/tasks-task-add.html)
- [Task Fields](https://apidocs.bitrix24.com/api-reference/tasks/fields.html)
- [Checklists API](https://apidocs.bitrix24.com/api-reference/tasks/checklist-item/)
- [Comments API](https://apidocs.bitrix24.com/api-reference/tasks/comment-item/)
- [Time Tracking API](https://apidocs.bitrix24.com/api-reference/tasks/elapsed-item/)
- [Webhooks Guide](https://helpdesk.bitrix24.com/open/21133100/)

---

## ✅ Готовность к реализации

**Степень уверенности:** 95%

Все необходимые данные для начала разработки:
- ✅ Webhook URL получен
- ✅ API методы изучены
- ✅ Архитектура спроектирована
- ✅ Структура проекта определена
- ✅ Список tools составлен
- ✅ Поля задач документированы

**Следующий шаг:** Начать реализацию с Этапа 1 - Инициализация проекта
