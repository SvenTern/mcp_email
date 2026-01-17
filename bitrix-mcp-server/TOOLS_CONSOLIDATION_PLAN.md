# План консолидации Tools Bitrix MCP Server

## 1. Текущее состояние

**Всего: 71 tool в 14 группах**

| Группа | Кол-во tools | Tools |
|--------|-------------|-------|
| task | 19 | create, get, list, update, delete, start, pause, complete, defer, renew, approve, disapprove, delegate, attach_files, counters, history, favorite_add, favorite_remove, get_fields |
| checklist | 6 | add, list, update, delete, complete, renew |
| group | 6 | list, get, members, my, search, access_check |
| user | 6 | list, get, current, search, fields, by_department |
| department | 5 | list, get, tree, employees, fields |
| list_element | 5 | add, get, update, delete, file_url |
| list_field | 5 | add, get, update, delete, types |
| list | 4 | add, get, update, delete |
| list_section | 4 | add, get, update, delete |
| comment | 4 | add, list, update, delete |
| time | 4 | add, list, update, delete |
| misc | 3 | test_connection, list_get_iblock_type, users_get |

---

## 2. Предлагаемая структура (71 → 12 tools)

### Принцип консолидации

Каждая группа объединяется в **один tool** с параметром `action`:

```typescript
{
  action: z.enum(['create', 'get', 'list', 'update', 'delete', ...]),
  // ... остальные параметры зависят от action
}
```

### 2.1 Новая структура tools

| № | Tool Name | Actions | Описание |
|---|-----------|---------|----------|
| 1 | `bitrix_task` | create, get, list, update, delete, start, pause, complete, defer, renew, approve, disapprove, delegate, attach_files, counters, history, favorite_add, favorite_remove, get_fields | Управление задачами |
| 2 | `bitrix_checklist` | add, list, update, delete, complete, renew | Чеклисты задач |
| 3 | `bitrix_comment` | add, list, update, delete | Комментарии к задачам |
| 4 | `bitrix_time` | add, list, update, delete | Учёт времени |
| 5 | `bitrix_user` | list, get, current, search, fields, by_department | Пользователи |
| 6 | `bitrix_department` | list, get, tree, employees, fields | Структура компании |
| 7 | `bitrix_group` | list, get, members, my, search, access_check | Рабочие группы |
| 8 | `bitrix_list` | add, get, update, delete, get_iblock_type | Универсальные списки |
| 9 | `bitrix_list_element` | add, get, update, delete, file_url | Элементы списков |
| 10 | `bitrix_list_field` | add, get, update, delete, types | Поля списков |
| 11 | `bitrix_list_section` | add, get, update, delete | Разделы списков |
| 12 | `bitrix_system` | test_connection, users_get | Системные функции |

**Итого: 12 tools вместо 71** (сокращение на 83%)

---

## 3. Детальная спецификация

### 3.1 bitrix_task

```typescript
{
  name: 'bitrix_task',
  description: 'Task management: create, read, update, delete tasks and manage their lifecycle',
  inputSchema: {
    action: z.enum([
      'create',      // Создать задачу
      'get',         // Получить задачу по ID
      'list',        // Список задач с фильтрами
      'update',      // Обновить задачу
      'delete',      // Удалить задачу
      'start',       // Начать выполнение
      'pause',       // Приостановить
      'complete',    // Завершить
      'defer',       // Отложить
      'renew',       // Возобновить
      'approve',     // Принять работу
      'disapprove',  // Отклонить работу
      'delegate',    // Делегировать
      'attach_files', // Прикрепить файлы
      'counters',    // Получить счётчики
      'history',     // История изменений
      'favorite_add',    // Добавить в избранное
      'favorite_remove', // Убрать из избранного
      'get_fields',  // Получить описание полей
    ]).describe('Action to perform'),

    // Параметры для create/update
    taskId: z.number().optional().describe('Task ID (required for get/update/delete/status actions)'),
    title: z.string().optional().describe('Task title (required for create)'),
    description: z.string().optional(),
    responsibleId: z.number().optional().describe('Responsible user ID'),
    deadline: z.string().optional(),
    priority: z.number().optional().describe('0=low, 1=normal, 2=high'),
    groupId: z.number().optional().describe('Workgroup ID'),
    parentId: z.number().optional().describe('Parent task ID'),
    accomplices: z.array(z.number()).optional(),
    auditors: z.array(z.number()).optional(),
    tags: z.array(z.string()).optional(),

    // Параметры для list
    filter: z.record(z.unknown()).optional(),
    select: z.array(z.string()).optional(),
    order: z.record(z.enum(['asc', 'desc'])).optional(),
    start: z.number().optional().describe('Pagination offset'),

    // Параметры для delegate
    newResponsibleId: z.number().optional(),

    // Параметры для attach_files
    fileIds: z.array(z.number()).optional(),
  }
}
```

### 3.2 bitrix_checklist

```typescript
{
  name: 'bitrix_checklist',
  description: 'Manage task checklists: add, list, update, delete, complete items',
  inputSchema: {
    action: z.enum(['add', 'list', 'update', 'delete', 'complete', 'renew']),
    taskId: z.number().describe('Task ID'),
    checklistId: z.number().optional().describe('Checklist item ID (for update/delete/complete/renew)'),
    title: z.string().optional().describe('Checklist item title (for add/update)'),
    isComplete: z.boolean().optional().describe('Completion status'),
  }
}
```

### 3.3 bitrix_comment

```typescript
{
  name: 'bitrix_comment',
  description: 'Manage task comments',
  inputSchema: {
    action: z.enum(['add', 'list', 'update', 'delete']),
    taskId: z.number().describe('Task ID'),
    commentId: z.number().optional().describe('Comment ID (for update/delete)'),
    text: z.string().optional().describe('Comment text (for add/update)'),
  }
}
```

### 3.4 bitrix_time

```typescript
{
  name: 'bitrix_time',
  description: 'Manage task time tracking records',
  inputSchema: {
    action: z.enum(['add', 'list', 'update', 'delete']),
    taskId: z.number().describe('Task ID'),
    recordId: z.number().optional().describe('Time record ID (for update/delete)'),
    seconds: z.number().optional().describe('Time spent in seconds'),
    comment: z.string().optional(),
    dateStart: z.string().optional(),
    dateStop: z.string().optional(),
  }
}
```

### 3.5 bitrix_user

```typescript
{
  name: 'bitrix_user',
  description: 'User/employee management',
  inputSchema: {
    action: z.enum(['list', 'get', 'current', 'search', 'fields', 'by_department']),
    userId: z.number().optional().describe('User ID (for get)'),
    departmentId: z.number().optional().describe('Department ID (for by_department)'),
    query: z.string().optional().describe('Search query (for search)'),
    filter: z.record(z.unknown()).optional(),
    start: z.number().optional(),
  }
}
```

### 3.6 bitrix_department

```typescript
{
  name: 'bitrix_department',
  description: 'Company org structure and departments',
  inputSchema: {
    action: z.enum(['list', 'get', 'tree', 'employees', 'fields']),
    departmentId: z.number().optional(),
    parentId: z.number().optional(),
    includeSubordinates: z.boolean().optional(),
    start: z.number().optional(),
  }
}
```

### 3.7 bitrix_group

```typescript
{
  name: 'bitrix_group',
  description: 'Workgroup management',
  inputSchema: {
    action: z.enum(['list', 'get', 'members', 'my', 'search', 'access_check']),
    groupId: z.number().optional().describe('Group ID'),
    query: z.string().optional().describe('Search query'),
    feature: z.string().optional().describe('Feature for access_check'),
    operation: z.string().optional().describe('Operation for access_check'),
    filter: z.record(z.unknown()).optional(),
    start: z.number().optional(),
  }
}
```

### 3.8 bitrix_list

```typescript
{
  name: 'bitrix_list',
  description: 'Universal lists (infoblock) management',
  inputSchema: {
    action: z.enum(['add', 'get', 'update', 'delete', 'get_iblock_type']),
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']).optional(),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    name: z.string().optional(),
    description: z.string().optional(),
    sort: z.number().optional(),
    bizproc: z.boolean().optional(),
    socnetGroupId: z.number().optional(),
    start: z.number().optional(),
  }
}
```

### 3.9 bitrix_list_element

```typescript
{
  name: 'bitrix_list_element',
  description: 'Universal list elements management',
  inputSchema: {
    action: z.enum(['add', 'get', 'update', 'delete', 'file_url']),
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    elementId: z.number().optional(),
    elementCode: z.string().optional(),
    name: z.string().optional(),
    sectionId: z.number().optional(),
    properties: z.record(z.unknown()).optional(),
    fieldId: z.string().optional().describe('Field ID for file_url action'),
    filter: z.record(z.unknown()).optional(),
    select: z.array(z.string()).optional(),
    socnetGroupId: z.number().optional(),
    start: z.number().optional(),
  }
}
```

### 3.10 bitrix_list_field

```typescript
{
  name: 'bitrix_list_field',
  description: 'Universal list fields management',
  inputSchema: {
    action: z.enum(['add', 'get', 'update', 'delete', 'types']),
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    fieldId: z.string().optional(),
    name: z.string().optional(),
    type: z.string().optional().describe('Field type (S, N, L, F, S:Date, etc.)'),
    code: z.string().optional(),
    isRequired: z.boolean().optional(),
    multiple: z.boolean().optional(),
    sort: z.number().optional(),
    defaultValue: z.string().optional(),
    listValues: z.array(z.string()).optional(),
    socnetGroupId: z.number().optional(),
  }
}
```

### 3.11 bitrix_list_section

```typescript
{
  name: 'bitrix_list_section',
  description: 'Universal list sections management',
  inputSchema: {
    action: z.enum(['add', 'get', 'update', 'delete']),
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    sectionId: z.number().optional(),
    sectionCode: z.string().optional(),
    name: z.string().optional(),
    parentSectionId: z.number().optional(),
    sort: z.number().optional(),
    active: z.boolean().optional(),
    filter: z.record(z.unknown()).optional(),
    select: z.array(z.string()).optional(),
    socnetGroupId: z.number().optional(),
  }
}
```

### 3.12 bitrix_system

```typescript
{
  name: 'bitrix_system',
  description: 'System utilities: test connection, bulk user operations',
  inputSchema: {
    action: z.enum(['test_connection', 'users_get']),
    userIds: z.array(z.number()).optional().describe('User IDs for users_get'),
  }
}
```

---

## 4. Преимущества консолидации

| Аспект | До | После | Улучшение |
|--------|-----|-------|-----------|
| Количество tools | 71 | 12 | -83% |
| Контекстное окно | Большое | Маленькое | Экономия токенов |
| Поиск tool | Сложный | Простой | UX |
| Семантика | Фрагментированная | Группированная | Понятность |

---

## 5. План миграции

### Этап 1: Создание новых tools
1. Создать `src/tools/consolidated/` директорию
2. Реализовать 12 новых tools с action-based подходом
3. Добавить роутинг action → существующие методы сервиса

### Этап 2: Python Wrapper
1. Заменить 71 функцию на 12 в `server.py`
2. Внутри каждой функции роутинг по action

### Этап 3: Тестирование
1. Протестировать все action для каждого tool
2. Проверить обратную совместимость

### Этап 4: Деплой
1. Пересборка Docker
2. Тестирование в production

---

## 6. Пример использования

### До (71 tools):
```json
// Создать задачу
{"tool": "bitrix_task_create", "args": {"title": "Test", "responsibleId": 1}}

// Получить задачу
{"tool": "bitrix_task_get", "args": {"taskId": 123}}

// Завершить задачу
{"tool": "bitrix_task_complete", "args": {"taskId": 123}}
```

### После (12 tools):
```json
// Создать задачу
{"tool": "bitrix_task", "args": {"action": "create", "title": "Test", "responsibleId": 1}}

// Получить задачу
{"tool": "bitrix_task", "args": {"action": "get", "taskId": 123}}

// Завершить задачу
{"tool": "bitrix_task", "args": {"action": "complete", "taskId": 123}}
```

---

## 7. Оценка

- **Сложность реализации**: Средняя
- **Риски**: Низкие (существующая логика сохраняется)
- **Время реализации**: 4-6 часов
- **Уверенность**: 90%

Готов к выполнению по подтверждению.
