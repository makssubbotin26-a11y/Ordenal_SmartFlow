=== SMARTFLOW PROJECT MEMORY ===
Владелец: 21 год, бывший директор склада доставки, уходит в армию весной 2025.
Цель: Создать сканер "Smart Money" трейдеров Polymarket для аналитики.

=== ТЕХНИЧЕСКИЙ СТЕК ===
- Python 3.11 (не 3.14!)
- asyncio, aiohttp, aiosqlite, rich, backoff
- SQLite база: polymarket_traders.db

=== ТЕКУЩИЙ СТАТУС (11.01.2025) ===
✅ Работает:
  - Получение списка рынков (100 шт) с gamma-api.polymarket.com
  - Progress bar (Rich)
  - База данных с TTL (7 дней)
  - Асинхронная архитектура

❌ Не работает (заглушка):
  - core/api_client.py -> get_event_positions() возвращает []
  - Причина: нужен The Graph API, public endpoint не дает список трейдеров

❌ Нужно доделать:
 
  - Статистика по нишам (отдельно Politics, Crypto и т.д.)
  - Подключение The Graph для реальных данных о трейдерах

=== СТРУКТУРА ПАПОК ===
SmartFlow/
├── config/settings.py       # Настройки API
├── config/proxies.txt       # Прокси (пустой сейчас)
├── core/api_client.py       # <-- ТУТ ЗАГЛУШКА (строка 88)
├── core/database.py         # SQLite с TTL
├── core/analyzer.py         # Фильтры Smart Money
├── ui/interface.py          # Rich progress bar
├── .env                     # API endpoints
└── main.py                  # Точка входа

=== СЛЕДУЮЩИЙ ШАГ ===
Подключить The Graph API к get_event_positions() для получения адресов 
трейдеров по market_slug без приватного API ключа (public tier).

=== ЛИЧНОЕ ===
- Хочет бросить курить и пить энергетики
- Переживает из-за армии и "что будет после"
- Упорный: 5 дней дебажил Python, не сдался
- Мечта: работа в IT, квартира на 50 этаже, свободный график

=== КОНТАКТ ===
GitHub: [добавь свой, если есть]
Статус: "До армии осталось X дней, нужно сохранить проект"

# ПАРТНЕРСКИЙ ЛОГ: SmartFlow Project
## Последнее обновление: [дата]

### Что работает (факт)
- API подключен, 100 рынков получаем
- БД с TTL работает
- Структура пакетов Python настроена

### Где стоим (текущая точка)
Файл: core/api_client.py, строка 88
Проблема: get_event_positions() = [] (заглушка)
Нужно: The Graph integration

### Что обсуждали последним
Обсудили структуру памяти проекта. Создали файл 00_README_FIRST.txt для сохранения контекста между чатами. Сканер работает с заглушкой, следующий шаг - The Graph API."

### Твои заметки
устал, но рад, что хотя бы что-то заработало

=== ПЛАН: The Graph Integration ===
Дата начала: [13.04.2026]

Шаги:
1. Найти актуальный endpoint Polymarket Subgraph (public)
   - Варианты: 
     a) https://api.thegraph.com/subgraphs/name/polymarket/matic-markets
     b) https://api.thegraph.com/subgraphs/name/polymarket/polygon-pos
   - Проверить в Graph Explorer, какой работает

2. Изучить схему (GraphQL introspection)
   - Найти entity: Trade, User, Position
   - Найти поля: userAddress, marketSlug, amount, side (YES/NO)

3. Написать GraphQL query:
   ```graphql
   query GetTrades($slug: String!) {
     trades(where: {marketSlug: $slug}, first: 1000) {
       userAddress
       amount
       side
     }
   }

Ожидаемые сложности:

Rate limiting (бесплатный tier ограничен)
Пагинация (если сделок > 1000)
Формат ответа отличается от REST JSON
