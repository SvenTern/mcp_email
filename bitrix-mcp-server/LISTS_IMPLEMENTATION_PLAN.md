# План доработки Bitrix MCP Server: Работа со Списками (Universal Lists)

## 1. Анализ API Bitrix24 для работы со Списками

### 1.1 Группы методов API

Bitrix24 REST API предоставляет 4 группы методов для работы со Списками:

| Группа | Методы | Назначение |
|--------|--------|------------|
| **Lists** | `lists.*` | Управление списками (инфоблоками) |
| **Elements** | `lists.element.*` | Управление элементами списков |
| **Fields** | `lists.field.*` | Управление полями списков |
| **Sections** | `lists.section.*` | Управление разделами списков |

### 1.2 Полный перечень методов API

#### Списки (lists.*)
| Метод | Описание |
|-------|----------|
| `lists.add` | Создание универсального списка |
| `lists.get` | Получение списка/списков |
| `lists.update` | Обновление списка |
| `lists.delete` | Удаление списка |
| `lists.get.iblock.type.id` | Получение идентификатора типа инфоблока |

#### Элементы (lists.element.*)
| Метод | Описание |
|-------|----------|
| `lists.element.add` | Создание элемента списка |
| `lists.element.get` | Получение элемента/элементов |
| `lists.element.update` | Обновление элемента |
| `lists.element.delete` | Удаление элемента |
| `lists.element.get.file.url` | Получение URL файла |

#### Поля (lists.field.*)
| Метод | Описание |
|-------|----------|
| `lists.field.add` | Создание поля списка |
| `lists.field.get` | Получение полей списка |
| `lists.field.update` | Обновление поля |
| `lists.field.delete` | Удаление поля |
| `lists.field.type.get` | Получение доступных типов полей |

#### Разделы (lists.section.*)
| Метод | Описание |
|-------|----------|
| `lists.section.add` | Создание раздела |
| `lists.section.get` | Получение разделов |
| `lists.section.update` | Обновление раздела |
| `lists.section.delete` | Удаление раздела |

---

## 2. Предлагаемые Tools для MCP Server

### 2.1 Tools для работы со Списками (5 tools)

| Tool Name | API Method | Описание |
|-----------|------------|----------|
| `bitrix_list_add` | `lists.add` | Создать универсальный список |
| `bitrix_list_get` | `lists.get` | Получить список/списки |
| `bitrix_list_update` | `lists.update` | Обновить параметры списка |
| `bitrix_list_delete` | `lists.delete` | Удалить список |
| `bitrix_list_get_iblock_type` | `lists.get.iblock.type.id` | Получить ID типа инфоблока |

### 2.2 Tools для работы с Элементами (5 tools)

| Tool Name | API Method | Описание |
|-----------|------------|----------|
| `bitrix_list_element_add` | `lists.element.add` | Создать элемент списка |
| `bitrix_list_element_get` | `lists.element.get` | Получить элемент/элементы |
| `bitrix_list_element_update` | `lists.element.update` | Обновить элемент |
| `bitrix_list_element_delete` | `lists.element.delete` | Удалить элемент |
| `bitrix_list_element_file_url` | `lists.element.get.file.url` | Получить URL файла элемента |

### 2.3 Tools для работы с Полями (5 tools)

| Tool Name | API Method | Описание |
|-----------|------------|----------|
| `bitrix_list_field_add` | `lists.field.add` | Создать поле списка |
| `bitrix_list_field_get` | `lists.field.get` | Получить поля списка |
| `bitrix_list_field_update` | `lists.field.update` | Обновить поле |
| `bitrix_list_field_delete` | `lists.field.delete` | Удалить поле |
| `bitrix_list_field_types` | `lists.field.type.get` | Получить доступные типы полей |

### 2.4 Tools для работы с Разделами (4 tools)

| Tool Name | API Method | Описание |
|-----------|------------|----------|
| `bitrix_list_section_add` | `lists.section.add` | Создать раздел |
| `bitrix_list_section_get` | `lists.section.get` | Получить разделы |
| `bitrix_list_section_update` | `lists.section.update` | Обновить раздел |
| `bitrix_list_section_delete` | `lists.section.delete` | Удалить раздел |

**Итого: 19 новых tools**

---

## 3. Детальная спецификация Tools

### 3.1 bitrix_list_add

```typescript
{
  name: 'bitrix_list_add',
  description: 'Create a new universal list in Bitrix24',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet'])
      .describe('List type: lists (standard), bitrix_processes (processes), lists_socnet (group lists)'),
    iblockCode: z.string().describe('Symbolic code for the list (unique identifier)'),
    name: z.string().describe('List display name'),
    description: z.string().optional().describe('List description'),
    sort: z.number().optional().describe('Sort order'),
    bizproc: z.boolean().optional().describe('Enable business process support'),
    socnetGroupId: z.number().optional().describe('Group ID for group lists'),
  }
}
```

### 3.2 bitrix_list_get

```typescript
{
  name: 'bitrix_list_get',
  description: 'Get list(s) from Bitrix24. Returns all accessible lists if no ID specified',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet'])
      .describe('List type'),
    iblockId: z.number().optional().describe('Specific list ID'),
    iblockCode: z.string().optional().describe('Specific list code'),
    socnetGroupId: z.number().optional().describe('Group ID for group lists'),
    start: z.number().optional().describe('Pagination offset (page size: 50)'),
  }
}
```

### 3.3 bitrix_list_element_add

```typescript
{
  name: 'bitrix_list_element_add',
  description: 'Create a new element in a Bitrix24 list',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional().describe('List ID'),
    iblockCode: z.string().optional().describe('List code'),
    elementCode: z.string().describe('Symbolic code for the element'),
    name: z.string().describe('Element name/title'),
    sectionId: z.number().optional().describe('Section ID (0 for root)'),
    fields: z.record(z.unknown()).optional()
      .describe('Custom field values as {PROPERTY_ID: value}'),
  }
}
```

### 3.4 bitrix_list_element_get

```typescript
{
  name: 'bitrix_list_element_get',
  description: 'Get element(s) from a Bitrix24 list',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    elementId: z.number().optional().describe('Specific element ID'),
    elementCode: z.string().optional().describe('Specific element code'),
    filter: z.record(z.unknown()).optional().describe('Filter conditions'),
    select: z.array(z.string()).optional().describe('Fields to return'),
    start: z.number().optional().describe('Pagination offset'),
  }
}
```

### 3.5 bitrix_list_field_add

```typescript
{
  name: 'bitrix_list_field_add',
  description: 'Add a new field to a Bitrix24 list',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
    name: z.string().describe('Field display name'),
    type: z.string().describe('Field type (S, N, L, F, S:Date, S:DateTime, etc.)'),
    code: z.string().optional().describe('Symbolic code (required for custom fields)'),
    isRequired: z.boolean().optional().describe('Make field required'),
    multiple: z.boolean().optional().describe('Allow multiple values'),
    sort: z.number().optional().describe('Sort order'),
    defaultValue: z.unknown().optional().describe('Default value'),
  }
}
```

### 3.6 bitrix_list_field_types

```typescript
{
  name: 'bitrix_list_field_types',
  description: 'Get available field types for a Bitrix24 list',
  inputSchema: {
    iblockTypeId: z.enum(['lists', 'bitrix_processes', 'lists_socnet']),
    iblockId: z.number().optional(),
    iblockCode: z.string().optional(),
  }
}
```

---

## 4. Типы полей Bitrix24 Lists

### 4.1 Базовые типы

| Код | Название | Описание |
|-----|----------|----------|
| `S` | Строка | Текстовое поле |
| `N` | Число | Числовое поле |
| `L` | Список | Выбор из списка значений |
| `F` | Файл | Загрузка файла |
| `G` | Привязка к разделам | Ссылка на раздел |
| `E` | Привязка к элементам | Ссылка на элемент |

### 4.2 Расширенные типы

| Код | Название | Описание |
|-----|----------|----------|
| `S:Date` | Дата | Только дата |
| `S:DateTime` | Дата/Время | Дата и время |
| `S:HTML` | HTML/текст | Форматированный текст |
| `E:EList` | Привязка к элементам списком | Множественный выбор элементов |
| `N:Sequence` | Счётчик | Автоинкремент |
| `S:ECrm` | Привязка к CRM | Ссылка на элемент CRM |
| `S:Money` | Деньги | Денежное поле |
| `S:DiskFile` | Файл (Диск) | Файл из Bitrix24.Диск |
| `S:map_yandex` | Яндекс.Карта | Геолокация |
| `S:employee` | Сотрудник | Ссылка на пользователя |

---

## 5. План реализации

### Этап 1: Типы данных (src/types/bitrix.ts)

Добавить интерфейсы:
- `BitrixList` - структура списка
- `BitrixListFields` - поля для создания/обновления списка
- `BitrixListFilter` - фильтр для получения списков
- `BitrixListElement` - структура элемента
- `BitrixListElementFields` - поля элемента
- `BitrixListField` - структура поля
- `BitrixListFieldType` - тип поля
- `BitrixListSection` - структура раздела

### Этап 2: Сервисный слой (src/services/bitrix-service.ts)

Добавить методы:

```typescript
// Lists
async createList(params): Promise<number>
async getLists(params): Promise<{lists: BitrixList[], total: number, next?: number}>
async updateList(params): Promise<boolean>
async deleteList(params): Promise<boolean>
async getIblockTypeId(): Promise<string>

// Elements
async createListElement(params): Promise<number>
async getListElements(params): Promise<{elements: BitrixListElement[], total: number, next?: number}>
async updateListElement(params): Promise<boolean>
async deleteListElement(params): Promise<boolean>
async getListElementFileUrl(params): Promise<string>

// Fields
async createListField(params): Promise<string>
async getListFields(params): Promise<BitrixListField[]>
async updateListField(params): Promise<boolean>
async deleteListField(params): Promise<boolean>
async getListFieldTypes(params): Promise<BitrixListFieldType[]>

// Sections
async createListSection(params): Promise<number>
async getListSections(params): Promise<BitrixListSection[]>
async updateListSection(params): Promise<boolean>
async deleteListSection(params): Promise<boolean>
```

### Этап 3: Tools (src/tools/list-tools.ts)

Создать файл `list-tools.ts` с 19 tools:
- 5 tools для списков
- 5 tools для элементов
- 5 tools для полей
- 4 tools для разделов

### Этап 4: Регистрация (src/tools/index.ts)

Добавить импорт и вызов `listTools(server, bitrixService)`

### Этап 5: Python Wrapper (wrapper/bitrix_mcp/server.py)

Добавить 19 Python-функций для проксирования вызовов к TypeScript серверу.

### Этап 6: Тестирование

1. Пересборка Docker образа
2. Тестирование каждого tool
3. Проверка обработки ошибок

---

## 6. Оценка уверенности

### Что понятно (уверенность >90%):
- Структура API Bitrix24 для списков
- Архитектура существующего MCP сервера
- Паттерн добавления новых tools
- Типы полей и их коды

### Что требует уточнения (уверенность 70-90%):
- Формат передачи значений для множественных полей
- Работа с файлами в полях типа F и S:DiskFile
- Особенности работы с бизнес-процессами (BIZPROC)

### Что может потребовать доработки в процессе:
- Обработка специфических ошибок API
- Формат ответов для сложных структур

**Общая уверенность в понимании задачи: 85%**

---

## 7. Источники документации

- [API Lists Overview](https://apidocs.bitrix24.ru/api-reference/lists/index.html)
- [lists.add](https://apidocs.bitrix24.ru/api-reference/lists/lists/lists-add.html)
- [lists.element.add](https://apidocs.bitrix24.ru/api-reference/lists/elements/lists-element-add.html)
- [lists.field.add](https://apidocs.bitrix24.ru/api-reference/lists/fields/lists-field-add.html)
- [lists.field.type.get](https://apidocs.bitrix24.ru/api-reference/lists/fields/lists-field-type-get.html)
- [GitHub: b24-rest-docs](https://github.com/bitrix-tools/b24-rest-docs/blob/main/api-reference/lists/index.md)
