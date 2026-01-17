# План организации почтового ящика Gmail
## svs.finpro@gmail.com

**Дата анализа:** 16 января 2026  
**Проанализировано:** ~100 последних писем  
**Общее количество писем в INBOX:** 36 675  
**Непрочитанных:** ~29 600

---

## 1. Анализ основных отправителей

### 1.1 Финансы и банки (высокий приоритет)

| Отправитель | Тип писем | Частота |
|-------------|-----------|---------|
| **Альфа-Банк** (Esupport@alfa-bank.info) | Реестры ИП Стецко С.А. | Ежедневно |
| **YooMoney** (reports@yoomoney.ru) | Реестры платежей/возвратов ИП Евстегнеева | 2 раза/день |
| **Interactive Brokers** (donotreply@interactivebrokers.com) | FYI: Analyst Ratings, Earnings, Statements | Несколько раз/день |
| **Stripe** (failed-payments@stripe.com) | Уведомления о платежах | По событиям |
| **Финам** (info.finam.ru) | Дайджесты, новости | Регулярно |

### 1.2 IT-сервисы и подписки

| Отправитель | Тип писем |
|-------------|-----------|
| **Anthropic** (mail.anthropic.com) | Чеки, уведомления о платежах |
| **AWS** (amazonaws.com, amazon.com) | Биллинг, поддержка |
| **Neo4j** (neo4j.com) | Биллинг, уведомления |
| **Selectel** (selectel.ru) | Биллинг, уведомления |
| **Cursor** (mail.cursor.com) | Новости продукта |
| **Replit** (mail.replit.com) | Новости, обновления |
| **Gamma** (stripe.com) | Чеки |
| **Termius** (news.termius.com) | Новости |

### 1.3 Образование и профессиональное развитие

| Отправитель | Тематика |
|-------------|----------|
| **AnalystPrep** (analystprep.com) | CFA подготовка |
| **HOCK Training** (hocktraining.com) | Финансовые сертификации |
| **Vibecoding1C** (vibecoding1c.ru, onerpa.ru) | 1С разработка |
| **Neural University** (neural-university.ru) | AI/ML |
| **Яндекс Практикум** (practicum.yandex.ru) | Английский |

### 1.4 Новости и аналитика

| Отправитель | Контент |
|-------------|---------|
| **The Information** (theinformation.com) | Tech Briefings |
| **Similarweb** (digital.similarweb.com) | Stock Intelligence |
| **Mobbin** (mobbin.com) | UI/UX |

### 1.5 Маркетинг и рассылки (низкий приоритет)

| Категория | Примеры |
|-----------|---------|
| **Ритейл РФ** | Лента, HUAWEI, SARTO REALE, Русские Корни |
| **Путешествия** | Яндекс Путешествия, Expedia, Aeroflot |
| **Развлечения Москва** | Остров Мечты, Театр Вахтангова, EventyOn |
| **Развлечения Аргентина** | Plateanet, Cinemark, Beneficios Galicia |
| **Здоровье** | МЕДСИ, Семейный доктор |
| **Детское** | Мамин Садик |

### 1.6 Безопасность и системные

| Отправитель | Тип |
|-------------|-----|
| **Google** (accounts.google.com) | Безопасность |
| **Link** (link.com) | Верификация |
| **Facebook** (facebookmail.com) | Уведомления |
| **Госуслуги** (gosuslugi.ru) | Гос. уведомления |

---

## 2. Предлагаемая структура папок

```
INBOX/
├── 00_Action_Required/          # Требует действия (платежи, подтверждения)
│
├── Finance/                      # Финансы
│   ├── Banking_RU/              # Российские банки
│   │   ├── Alfa_Bank/           # Альфа-Банк (реестры ИП)
│   │   └── VTB/                 # ВТБ
│   ├── Banking_INT/             # Международные
│   │   └── Interactive_Brokers/ # IBKR (выписки, FYI)
│   ├── Payments/                # Платёжные системы
│   │   ├── YooMoney/            # ЮКасса/YooMoney
│   │   └── Stripe/              # Stripe чеки
│   └── Investments/             # Инвестиции
│       ├── IBKR_Analytics/      # Аналитика IBKR
│       └── Finam/               # Финам
│
├── Business/                     # Бизнес
│   ├── IP_Stetsko/              # ИП Стецко С.А.
│   └── IP_Evstigneeva/          # ИП Евстегнеева Е.К.
│
├── Tech_Services/               # IT-сервисы
│   ├── Cloud/                   # Облака
│   │   ├── AWS/
│   │   ├── Selectel/
│   │   └── Neo4j/
│   ├── AI_Tools/                # AI инструменты
│   │   ├── Anthropic/           # Claude
│   │   ├── Cursor/
│   │   └── Replit/
│   └── Dev_Tools/               # Инструменты разработки
│       ├── GitHub/
│       └── Other/
│
├── Education/                   # Образование
│   ├── CFA/                     # CFA подготовка
│   ├── 1C_Dev/                  # 1С разработка
│   └── Languages/               # Языки
│
├── News/                        # Новости и аналитика
│   ├── Tech/                    # Технологии
│   │   ├── The_Information/
│   │   └── Product_Updates/
│   └── Markets/                 # Рынки
│       └── Similarweb/
│
├── Personal/                    # Личное
│   ├── Family/                  # Семья (Мамин Садик и т.д.)
│   ├── Health/                  # Здоровье (МЕДСИ и т.д.)
│   └── Travel/                  # Путешествия
│
├── Security/                    # Безопасность
│   ├── Google/                  # Google alerts
│   ├── Verification_Codes/      # Коды подтверждения
│   └── Login_Alerts/            # Уведомления о входе
│
├── Marketing/                   # Маркетинг (низкий приоритет)
│   ├── Retail_RU/               # Ритейл Россия
│   ├── Entertainment_RU/        # Развлечения Россия
│   ├── Entertainment_AR/        # Развлечения Аргентина
│   └── Offers/                  # Акции и предложения
│
└── Archive/                     # Архив
    ├── 2025/
    └── 2024/
```

---

## 3. Правила автоматической сортировки

### 3.1 Высокий приоритет (немедленная обработка)

| Условие | Действие |
|---------|----------|
| `from:*@alfa-bank.info` + `subject:Reestr` | → Business/IP_Stetsko |
| `from:reports@yoomoney.ru` | → Business/IP_Evstigneeva |
| `from:*@interactivebrokers.com` + `subject:Statement` | → Finance/Banking_INT/Interactive_Brokers |
| `from:failed-payments@*` | → 00_Action_Required |
| `from:*invoice*@stripe.com` | → Finance/Payments/Stripe |

### 3.2 Средний приоритет

| Условие | Действие |
|---------|----------|
| `from:*@interactivebrokers.com` + `subject:FYI` | → Finance/Investments/IBKR_Analytics |
| `from:*@anthropic.com` | → Tech_Services/AI_Tools/Anthropic |
| `from:*@theinformation.com` | → News/Tech/The_Information |
| `from:*@analystprep.com` | → Education/CFA |
| `from:*vibecoding*` OR `from:*onerpa*` | → Education/1C_Dev |

### 3.3 Низкий приоритет (можно архивировать)

| Условие | Действие |
|---------|----------|
| `from:*@feverup.com` OR `from:*@plateanet.com` | → Marketing/Entertainment_AR |
| `from:*@dreamisland.ru` OR `from:*@vakhtangov.ru` | → Marketing/Entertainment_RU |
| `from:*@lentamail.com` OR `from:*@huawei.ru` | → Marketing/Retail_RU |
| `from:promo@travel.yandex.ru` | → Marketing/Offers |

---

## 4. Рекомендации по очистке

### 4.1 Кандидаты на массовое удаление

1. **IBKR FYI письма** (старше 30 дней) — информационные, не требуют хранения
2. **Marketing рассылки** (старше 7 дней) — акции уже неактуальны
3. **Verification codes** (старше 1 дня) — одноразовые

### 4.2 Кандидаты на отписку

- Plateanet (аргентинский театр) — неактуально
- Beneficios Galicia — неактуально  
- Cinemark Argentina — неактуально
- Русские Корни — спам-характер
- Большинство retail-рассылок

### 4.3 Важно сохранить

- Все банковские реестры (Альфа-Банк, YooMoney)
- Чеки и квитанции (Stripe, Anthropic, AWS)
- Переписка с поддержкой (AWS Case, Selectel)

---

## 5. План внедрения

### Фаза 1: Создание структуры (1 день)
- [ ] Создать основные папки верхнего уровня
- [ ] Создать подпапки для финансов и бизнеса

### Фаза 2: Настройка фильтров Gmail (1-2 дня)
- [ ] Настроить фильтры для высокоприоритетных отправителей
- [ ] Настроить фильтры для маркетинговых рассылок

### Фаза 3: Массовая сортировка (2-3 дня)
- [ ] Отсортировать существующие письма по категориям
- [ ] Удалить устаревший маркетинг

### Фаза 4: Отписка от рассылок (1 день)
- [ ] Отписаться от неактуальных рассылок
- [ ] Настроить спам-фильтры

---

## 6. Статистика текущего состояния

| Метрика | Значение |
|---------|----------|
| Всего писем | 36 675 |
| Непрочитанных | ~29 600 (80%) |
| Папок создано | 19 |
| Активная папка IHateSpammers | 1 270 писем |
| Спам | 297 |

---

## 7. Ожидаемый результат

После внедрения:
- **Inbox Zero** — возможен при регулярной обработке
- **Время на обработку почты** — сократится на 50-70%
- **Важные письма** — не будут теряться в потоке
- **Архив** — структурированный и доступный для поиска

---

*Документ подготовлен на основе анализа почтового ящика через MCP Email API*
