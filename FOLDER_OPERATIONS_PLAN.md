# План доработки Email MCP Server: Операции с папками и перемещение писем

## Обзор

Добавление 6 новых функций для управления папками и перемещения/копирования писем.

## Новые функции

### 1. Операции с письмами

| Функция | Описание | Параметры |
|---------|----------|-----------|
| `imap_move_emails` | Переместить письма в папку | `accountId`, `uids: List[int]`, `source_folder`, `target_folder` |
| `imap_copy_emails` | Скопировать письма в папку | `accountId`, `uids: List[int]`, `source_folder`, `target_folder` |

### 2. Операции с папками

| Функция | Описание | Параметры |
|---------|----------|-----------|
| `imap_create_folder` | Создать папку | `accountId`, `folder_name`, `parent_folder?` |
| `imap_delete_folder` | Удалить папку | `accountId`, `folder_name` |
| `imap_rename_folder` | Переименовать папку | `accountId`, `old_name`, `new_name` |

## Технические детали

### imapflow API

```typescript
// Move emails (IMAP MOVE command, RFC 6851)
await client.messageMove(uids, targetFolder, { uid: true });

// Copy emails (IMAP COPY command)
await client.messageCopy(uids, targetFolder, { uid: true });

// Create folder
await client.mailboxCreate(folderPath);

// Delete folder
await client.mailboxDelete(folderPath);

// Rename folder
await client.mailboxRename(oldPath, newPath);
```

### Fallback для MOVE

Некоторые серверы не поддерживают MOVE (RFC 6851). Fallback:
1. COPY в целевую папку
2. Пометить оригиналы как \Deleted
3. EXPUNGE

## План реализации

### Этап 1: TypeScript (imap-mcp-server)

**Файл:** `src/services/imap-service.ts`

```typescript
// Добавить методы:
async moveEmails(accountId: string, uids: number[], sourceFolder: string, targetFolder: string): Promise<{ moved: number }>;
async copyEmails(accountId: string, uids: number[], sourceFolder: string, targetFolder: string): Promise<{ copied: number }>;
async createFolder(accountId: string, folderPath: string): Promise<void>;
async deleteFolder(accountId: string, folderPath: string): Promise<void>;
async renameFolder(accountId: string, oldPath: string, newPath: string): Promise<void>;
```

**Файл:** `src/tools/folder-tools.ts`

Добавить регистрацию 5 новых инструментов.

### Этап 2: Python Wrapper (server.py)

**Файл:** `src/email_mcp/server.py`

```python
@mcp.tool()
async def imap_move_emails(
    accountId: str,
    uids: List[int],
    target_folder: str,
    source_folder: str = "INBOX"
) -> dict:
    """Move emails to another folder."""

@mcp.tool()
async def imap_copy_emails(
    accountId: str,
    uids: List[int],
    target_folder: str,
    source_folder: str = "INBOX"
) -> dict:
    """Copy emails to another folder."""

@mcp.tool()
async def imap_create_folder(
    accountId: str,
    folder_name: str,
    parent_folder: str = None
) -> dict:
    """Create a new folder."""

@mcp.tool()
async def imap_delete_folder(
    accountId: str,
    folder_name: str
) -> dict:
    """Delete a folder."""

@mcp.tool()
async def imap_rename_folder(
    accountId: str,
    old_name: str,
    new_name: str
) -> dict:
    """Rename a folder."""
```

### Этап 3: Сборка и деплой

1. `node build.mjs` - сборка TypeScript
2. Создание tarball с обновлениями
3. Копирование на сервер
4. Перезапуск контейнера

### Этап 4: Тестирование

| Тест | Ожидаемый результат |
|------|---------------------|
| Создать папку "Test" | Папка появляется в list_folders |
| Скопировать письмо в "Test" | Письмо в обеих папках |
| Переместить письмо в "Test" | Письмо только в "Test" |
| Переименовать "Test" → "Archive" | Папка переименована |
| Удалить папку "Archive" | Папка удалена |

## Оценка трудозатрат

| Этап | Время |
|------|-------|
| TypeScript реализация | ~30 мин |
| Python wrapper | ~15 мин |
| Тестирование | ~15 мин |
| **Итого** | **~1 час** |

## Риски и ограничения

1. **MOVE не поддерживается** - некоторые старые IMAP серверы. Решение: fallback через COPY + DELETE.

2. **Вложенные папки** - разделитель папок различается (`.` vs `/`). Решение: использовать `mailboxCreate` который автоматически создаёт родительские папки.

3. **Специальные папки** - нельзя удалить INBOX, Sent, Trash. Решение: проверка перед удалением.

## Структура изменений

```
imap-mcp-server/
├── src/
│   ├── services/
│   │   └── imap-service.ts  # +5 методов
│   └── tools/
│       └── folder-tools.ts  # +5 инструментов
└── dist/
    └── index.js             # пересборка

src/email_mcp/
└── server.py                # +5 wrapper функций
```

## Статус

- [ ] TypeScript: imap-service.ts
- [ ] TypeScript: folder-tools.ts
- [ ] Сборка
- [ ] Python: server.py
- [ ] Деплой
- [ ] Тестирование
