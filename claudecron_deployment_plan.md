# План развёртывания ClaudeCron MCP-сервера

## Обзор проекта

**ClaudeCron** — MCP-сервер для автоматизации задач в Claude Code с поддержкой:
- Запуска bash-команд по расписанию (cron)
- Запуска AI-задач (subagent) по событиям
- Отслеживания изменений файлов (file watcher)
- Интеграции с Claude Code hooks

**Протокол**: MCP Streamable HTTP (спецификация 2025-11-25)

---

## Архитектура решения

```
┌─────────────────────────────────────────────────────────────────┐
│                    Удалённый сервер                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  Reverse Proxy (nginx)                      ││
│  │                  https://mcp.svsfinpro.ru/cron/mcp           ││
│  │                  - SSL termination                          ││
│  │                  - Origin validation                        ││
│  │                  - Rate limiting                            ││
│  └──────────────────────────┬──────────────────────────────────┘│
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────────┐│
│  │              ClaudeCron MCP Server                          ││
│  │              (Node.js + Streamable HTTP)                    ││
│  │                                                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ ││
│  │  │ Cron Tasks  │  │ File Watch  │  │ AI Subagent Tasks   │ ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘ ││
│  │                                                             ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │              SQLite Database                            │││
│  │  │              ~/.claude/claudecron/tasks.db              │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Клиенты                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Claude Web   │  │ Claude       │  │ Claude Code CLI      │  │
│  │              │  │ Desktop      │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Фазы разработки

### Фаза 1: Подготовка инфраструктуры

#### 1.1 Настройка сервера
- [ ] Установка Node.js 18+ на сервер
- [ ] Установка npm/pnpm
- [ ] Настройка systemd для автозапуска
- [ ] Создание пользователя `claudecron` с ограниченными правами

#### 1.2 Безопасность
- [ ] Настройка firewall (ufw/iptables)
- [ ] Установка и настройка nginx как reverse proxy
- [ ] Получение SSL-сертификата (Let's Encrypt)
- [ ] Настройка валидации Origin header

---

### Фаза 2: Адаптация ClaudeCron под Streamable HTTP

#### 2.1 Создание HTTP-транспорта

Текущая версия ClaudeCron использует stdio транспорт. Необходимо добавить Streamable HTTP:

```typescript
// src/transports/streamable-http.ts

import express, { Request, Response } from 'express';
import { randomUUID } from 'crypto';

interface Session {
  id: string;
  createdAt: Date;
  lastActivity: Date;
}

export class StreamableHttpTransport {
  private app: express.Application;
  private sessions: Map<string, Session> = new Map();
  private sseClients: Map<string, Response[]> = new Map();

  constructor(private port: number = 3000) {
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware() {
    this.app.use(express.json());

    // Origin validation (ОБЯЗАТЕЛЬНО для безопасности)
    this.app.use((req, res, next) => {
      const origin = req.headers.origin;
      const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',') || [];

      if (origin && !allowedOrigins.includes(origin)) {
        return res.status(403).json({ error: 'Origin not allowed' });
      }
      next();
    });
  }

  private setupRoutes() {
    // Единый MCP endpoint
    this.app.post('/mcp', this.handlePost.bind(this));
    this.app.get('/mcp', this.handleGet.bind(this));
    this.app.delete('/mcp', this.handleDelete.bind(this));
  }

  private async handlePost(req: Request, res: Response) {
    const sessionId = req.headers['mcp-session-id'] as string;
    const accept = req.headers.accept || '';

    // Проверка Accept header
    if (!accept.includes('application/json') && !accept.includes('text/event-stream')) {
      return res.status(400).json({ error: 'Invalid Accept header' });
    }

    const message = req.body;

    // Initialize request - создаём новую сессию
    if (message.method === 'initialize') {
      const newSessionId = randomUUID();
      this.sessions.set(newSessionId, {
        id: newSessionId,
        createdAt: new Date(),
        lastActivity: new Date()
      });

      res.setHeader('Mcp-Session-Id', newSessionId);
      return res.json(await this.handleMessage(message));
    }

    // Проверка сессии для других запросов
    if (!sessionId || !this.sessions.has(sessionId)) {
      return res.status(400).json({ error: 'Invalid or missing session ID' });
    }

    // Обновляем активность сессии
    const session = this.sessions.get(sessionId)!;
    session.lastActivity = new Date();

    // Обработка notification (без ответа)
    if (!message.id) {
      res.status(202).end();
      await this.handleMessage(message);
      return;
    }

    // SSE streaming или JSON response
    if (accept.includes('text/event-stream')) {
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      const response = await this.handleMessage(message);
      const eventId = randomUUID();
      res.write(`data: ${JSON.stringify(response)}\nid: ${eventId}\n\n`);
      res.end();
    } else {
      res.json(await this.handleMessage(message));
    }
  }

  private async handleGet(req: Request, res: Response) {
    const sessionId = req.headers['mcp-session-id'] as string;

    if (!sessionId || !this.sessions.has(sessionId)) {
      return res.status(400).json({ error: 'Invalid session ID' });
    }

    // SSE stream для server-to-client notifications
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Регистрируем клиента для уведомлений
    if (!this.sseClients.has(sessionId)) {
      this.sseClients.set(sessionId, []);
    }
    this.sseClients.get(sessionId)!.push(res);

    // Cleanup при отключении
    req.on('close', () => {
      const clients = this.sseClients.get(sessionId);
      if (clients) {
        const index = clients.indexOf(res);
        if (index > -1) clients.splice(index, 1);
      }
    });
  }

  private async handleDelete(req: Request, res: Response) {
    const sessionId = req.headers['mcp-session-id'] as string;

    if (sessionId && this.sessions.has(sessionId)) {
      this.sessions.delete(sessionId);
      this.sseClients.delete(sessionId);
      res.status(204).end();
    } else {
      res.status(404).json({ error: 'Session not found' });
    }
  }

  private async handleMessage(message: any): Promise<any> {
    // Здесь подключается основная логика ClaudeCron
    // Делегируем обработку в существующий handler
    return { jsonrpc: '2.0', id: message.id, result: {} };
  }

  public start() {
    this.app.listen(this.port, '127.0.0.1', () => {
      console.log(`ClaudeCron MCP server listening on port ${this.port}`);
    });
  }
}
```

#### 2.2 Интеграция с существующими инструментами ClaudeCron

```typescript
// src/tools/index.ts

export const CLAUDECRON_TOOLS = {
  // Добавление задачи
  claudecron_add_task: {
    description: 'Create a new scheduled task',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Task name' },
        type: {
          type: 'string',
          enum: ['bash', 'subagent'],
          description: 'Task type'
        },
        schedule: {
          type: 'string',
          description: 'Cron expression (5 or 6 fields)'
        },
        command: { type: 'string', description: 'Bash command (for bash type)' },
        prompt: { type: 'string', description: 'AI prompt (for subagent type)' },
        timezone: { type: 'string', default: 'UTC' },
        enabled: { type: 'boolean', default: true }
      },
      required: ['name', 'type', 'schedule']
    }
  },

  // Список задач
  claudecron_list_tasks: {
    description: 'List all scheduled tasks',
    inputSchema: {
      type: 'object',
      properties: {
        status: {
          type: 'string',
          enum: ['all', 'enabled', 'disabled'],
          default: 'all'
        }
      }
    }
  },

  // Запуск задачи вручную
  claudecron_run_task: {
    description: 'Run a task immediately',
    inputSchema: {
      type: 'object',
      properties: {
        taskId: { type: 'string', description: 'Task ID to run' }
      },
      required: ['taskId']
    }
  },

  // Удаление задачи
  claudecron_delete_task: {
    description: 'Delete a scheduled task',
    inputSchema: {
      type: 'object',
      properties: {
        taskId: { type: 'string', description: 'Task ID to delete' }
      },
      required: ['taskId']
    }
  },

  // История выполнения
  claudecron_get_history: {
    description: 'Get task execution history',
    inputSchema: {
      type: 'object',
      properties: {
        taskId: { type: 'string', description: 'Filter by task ID' },
        limit: { type: 'number', default: 50 },
        status: {
          type: 'string',
          enum: ['all', 'success', 'failed'],
          default: 'all'
        }
      }
    }
  },

  // Управление задачей
  claudecron_toggle_task: {
    description: 'Enable or disable a task',
    inputSchema: {
      type: 'object',
      properties: {
        taskId: { type: 'string' },
        enabled: { type: 'boolean' }
      },
      required: ['taskId', 'enabled']
    }
  }
};
```

---

### Фаза 3: Конфигурация и безопасность

#### 3.1 Конфигурационный файл

```typescript
// config/server.config.ts

export interface ServerConfig {
  // HTTP сервер
  port: number;
  host: string;

  // Безопасность
  allowedOrigins: string[];
  rateLimitPerMinute: number;
  sessionTimeoutMs: number;

  // База данных
  dbPath: string;

  // Логирование
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  logPath: string;

  // Ограничения задач
  maxConcurrentTasks: number;
  taskTimeoutMs: number;

  // AI задачи
  anthropicApiKey?: string;
  defaultModel: string;
}

export const defaultConfig: ServerConfig = {
  port: 3010,  // Порт для cron MCP сервера
  host: '127.0.0.1',

  allowedOrigins: [],
  rateLimitPerMinute: 100,
  sessionTimeoutMs: 3600000, // 1 час

  dbPath: '~/.claudecron/tasks.db',

  logLevel: 'info',
  logPath: '~/.claudecron/logs',

  maxConcurrentTasks: 10,
  taskTimeoutMs: 300000, // 5 минут

  defaultModel: 'claude-sonnet-4-20250514'
};
```

#### 3.2 Nginx конфигурация

```nginx
# /etc/nginx/sites-available/claudecron

upstream cron_mcp {
    server 127.0.0.1:3010;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name mcp.svsfinpro.ru;

    ssl_certificate /etc/letsencrypt/live/mcp.svsfinpro.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.svsfinpro.ru/privkey.pem;

    # Безопасность
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=10r/s;
    limit_req zone=mcp_limit burst=20 nodelay;

    location /cron/ {
        # Проксирование к ClaudeCron (порт 3010)
        proxy_pass http://127.0.0.1:3010/;
        proxy_http_version 1.1;

        # SSE support
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts для long-polling
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}

server {
    listen 80;
    server_name mcp.svsfinpro.ru;
    return 301 https://$server_name$request_uri;
}
```

#### 3.3 Systemd сервис

```ini
# Docker Compose конфигурация (рекомендуется)
# /opt/cron-mcp-server/docker-compose.yml

version: '3.8'

services:
  cron-mcp:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: cron-mcp-server
    ports:
      - "3010:8080"
    environment:
      - NODE_ENV=production
      - PORT=8080
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

### Фаза 4: Развёртывание

#### 4.1 Скрипт развёртывания

```bash
#!/bin/bash
# deploy.sh

set -e

REMOTE_HOST="217.199.253.8"
REMOTE_USER="root"
REMOTE_DIR="/opt/cron-mcp-server"
CONTAINER_NAME="cron-mcp-server"

echo "🚀 Deploying ClaudeCron..."

# 1. Сборка
echo "📦 Building..."
npm run build

# 2. Копирование файлов
echo "📤 Uploading..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '.git' \
  ./ $SERVER_USER@$SERVER_HOST:$DEPLOY_PATH/

# 3. Установка зависимостей на сервере
echo "📥 Installing dependencies..."
ssh $SERVER_USER@$SERVER_HOST "cd $DEPLOY_PATH && npm ci --production"

# 4. Перезапуск сервиса
echo "🔄 Restarting service..."
ssh $SERVER_USER@$SERVER_HOST "sudo systemctl restart claudecron"

# 5. Проверка статуса
echo "✅ Checking status..."
ssh $SERVER_USER@$SERVER_HOST "sudo systemctl status claudecron --no-pager"

echo "🎉 Deployment complete!"
```

#### 4.2 Проверка работоспособности

```bash
# Тест endpoint
curl -X POST https://mcp.svsfinpro.ru/cron/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-11-25",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

---

### Фаза 5: Клиентская конфигурация

#### 5.1 Claude Desktop / Claude Web

```json
{
  "mcpServers": {
    "cron": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/cron/mcp"]
    }
  }
}
```

#### 5.2 Claude Code CLI

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "cron": {
      "command": "npx",
      "args": ["mcp-remote", "https://mcp.svsfinpro.ru/cron/mcp"]
    }
  }
}
```

---

## URL Endpoints

После развёртывания сервер будет доступен по следующим адресам:

| Endpoint | URL | Описание |
|----------|-----|----------|
| Info | `https://mcp.svsfinpro.ru/cron/` | Информация о сервере |
| Health | `https://mcp.svsfinpro.ru/cron/health` | Health check |
| MCP | `https://mcp.svsfinpro.ru/cron/mcp` | MCP endpoint |

---

## Примеры использования

### Пример 1: Ежедневный backup

```json
{
  "method": "tools/call",
  "params": {
    "name": "claudecron_add_task",
    "arguments": {
      "name": "daily-backup",
      "type": "bash",
      "schedule": "0 2 * * *",
      "command": "/opt/scripts/backup.sh",
      "timezone": "Europe/Moscow"
    }
  }
}
```

### Пример 2: AI-задача код-ревью

```json
{
  "method": "tools/call",
  "params": {
    "name": "claudecron_add_task",
    "arguments": {
      "name": "weekly-code-review",
      "type": "subagent",
      "schedule": "0 9 * * 1",
      "prompt": "Review all commits from last week in /project, summarize changes and potential issues",
      "timezone": "UTC"
    }
  }
}
```

### Пример 3: Мониторинг файлов

```json
{
  "method": "tools/call",
  "params": {
    "name": "claudecron_add_task",
    "arguments": {
      "name": "config-watcher",
      "type": "bash",
      "trigger": {
        "type": "file-watch",
        "path": "/etc/nginx/nginx.conf"
      },
      "command": "nginx -t && systemctl reload nginx"
    }
  }
}
```

---

## Чек-лист готовности

### Инфраструктура
- [ ] Сервер с Node.js 18+
- [ ] Nginx установлен и настроен
- [ ] SSL-сертификат получен
- [ ] Firewall настроен (порты 80, 443)
- [ ] Systemd сервис создан

### Безопасность
- [ ] Origin validation включена
- [ ] Rate limiting настроен
- [ ] Сервер слушает только localhost
- [ ] Логирование настроено
- [ ] Backup базы данных настроен

### Тестирование
- [ ] Initialize request работает
- [ ] Создание задачи работает
- [ ] Cron scheduling работает
- [ ] SSE streaming работает
- [ ] Session management работает

### Документация
- [ ] API документация
- [ ] Runbook для операторов
- [ ] Схема мониторинга

---

## Ресурсы

- [ClaudeCron GitHub](https://github.com/phildougherty/claudecron)
- [MCP Streamable HTTP Spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP Streamable HTTP Examples](https://github.com/invariantlabs-ai/mcp-streamable-http)
- [Building Automated Claude Code Workers](https://www.blle.co/blog/automated-claude-code-workers)

---

## Временные оценки

| Фаза | Описание |
|------|----------|
| Фаза 1 | Подготовка инфраструктуры |
| Фаза 2 | Адаптация под Streamable HTTP |
| Фаза 3 | Конфигурация и безопасность |
| Фаза 4 | Развёртывание |
| Фаза 5 | Клиентская интеграция |

---

*Документ создан: 2026-01-16*
