# Новая схема работы Docker MCP Orchestrator

## 🎯 Цели

1. **Автоматическое обнаружение** всех MCP серверов из Docker MCP Toolkit
2. **Минимум токенов при старте** - только краткий каталог серверов (без tools)
3. **AI сам выбирает** какие серверы активировать
4. **Tools загружаются только после активации** сервера
5. **Умные рекомендации** на основе задачи

---

## 📊 Схема работы

### Этап 1: Инициализация Orchestrator

```
┌─────────────────────────────────────────────────────────┐
│         Docker MCP Orchestrator (старт)                 │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  1. Запрос к Docker MCP Toolkit                        │
│     docker mcp server ls                                │
│                                                          │
│  2. Обнаружение всех доступных серверов                 │
│     - context7                                          │
│     - playwright                                        │
│     - github                                            │
│     - redis                                             │
│     - postgres                                          │
│     - ... (все что есть в Docker MCP Toolkit)          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  3. Получение метаданных каждого сервера                │
│     docker mcp server inspect <name>                    │
│                                                          │
│     Для каждого сервера:                                │
│     - Название                                          │
│     - Описание (если есть)                              │
│     - Категория (автоопределение или из конфига)       │
│     - Требует ли аутентификацию                         │
│     - Статус (активен/неактивен)                        │
│     - Количество tools (БЕЗ деталей tools!)            │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  4. Кэширование метаданных                              │
│     - В памяти (для быстрого доступа)                  │
│     - Периодическая синхронизация                       │
└─────────────────────────────────────────────────────────┘
```

### Этап 2: Первое взаимодействие AI с Orchestrator

```
┌─────────────────────────────────────────────────────────┐
│                    AI (Claude/Cursor)                   │
│                                                          │
│  При первом запросе AI получает:                        │
│  - Только 8 инструментов orchestrator                   │
│  - ~500-1000 токенов (минимум!)                         │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  AI вызывает: list_available_servers()                   │
│                                                          │
│  Возвращает КРАТКИЙ каталог:                            │
│  ┌──────────────────────────────────────┐              │
│  │ 📦 Available MCP Servers (12)        │              │
│  │                                       │              │
│  │ 🗄️ Database                          │              │
│  │   • redis (⚪) - Redis cache         │              │
│  │     ~15 tools                        │              │
│  │   • postgres (⚪) - PostgreSQL       │              │
│  │     ~1 tool                          │              │
│  │                                       │              │
│  │ 🌐 Browser                           │              │
│  │   • playwright (⚪) - Web automation │              │
│  │     ~15 tools                        │              │
│  │                                       │              │
│  │ ... (без деталей tools!)             │              │
│  └──────────────────────────────────────┘              │
│                                                          │
│  ~200-500 токенов (вместо 15-20k!)                     │
└─────────────────────────────────────────────────────────┘
```

### Этап 3: AI выбирает нужные серверы

```
┌─────────────────────────────────────────────────────────┐
│  Пользователь: "Настрой Redis кэш"                      │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  AI анализирует задачу:                                 │
│  - Нужен Redis → активировать redis                    │
│  - Для документации → активировать context7             │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  AI вызывает: activate_server("redis")                  │
│                                                          │
│  Orchestrator:                                           │
│  1. docker mcp server enable redis                      │
│  2. Получает tools от redis сервера                     │
│  3. Кэширует tools в памяти                             │
│  4. Возвращает AI список tools redis                    │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  AI получает:                                            │
│  ┌──────────────────────────────────────┐              │
│  │ ✅ redis activated                    │              │
│  │                                       │              │
│  │ Available tools (15):                 │              │
│  │ • redis_get(key)                     │              │
│  │ • redis_set(key, value)              │              │
│  │ • redis_del(key)                     │              │
│  │ • redis_keys(pattern)                │              │
│  │ • redis_hget(hash, field)            │              │
│  │ • redis_hset(hash, field, value)     │              │
│  │ • redis_lpush(list, value)           │              │
│  │ • redis_rpush(list, value)           │              │
│  │ • redis_lrange(list, start, end)     │              │
│  │ • redis_config_get(parameter)         │              │
│  │ • redis_config_set(parameter, value) │              │
│  │ • redis_info(section)                │              │
│  │ • redis_ping()                       │              │
│  │ • redis_ttl(key)                     │              │
│  │ • redis_expire(key, seconds)        │              │
│  └──────────────────────────────────────┘              │
│                                                          │
│  ~1000-2000 токенов (только для redis!)                │
└─────────────────────────────────────────────────────────┘
```

### Этап 4: AI использует tools

```
┌─────────────────────────────────────────────────────────┐
│  AI теперь может использовать Redis tools:              │
│  - redis_set("session:user123", "data")                │
│  - redis_config_set("maxmemory", "256mb")               │
│  - redis_get("session:user123")                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Полный Workflow

### Сценарий 1: Простая задача

```
1. AI стартует
   → Видит 8 инструментов orchestrator (~500 токенов)

2. AI вызывает list_available_servers()
   → Получает краткий каталог (~300 токенов)
   → Всего: ~800 токенов (вместо 15-20k!)

3. Пользователь: "Сделай скриншот сайта"
   → AI видит в каталоге: playwright
   → AI вызывает activate_server("playwright")
   → AI получает tools playwright (~2000 токенов)
   → AI использует browser_navigate, browser_screenshot

4. После работы
   → AI вызывает deactivate_server("playwright")
   → Tools playwright удаляются из контекста
```

### Сценарий 2: Сложная задача с документацией

```
1. Пользователь: "Настрой Redis кэш и создай GitHub issue"

2. AI анализирует:
   → Нужен redis
   → Нужен github
   → Для документации нужен context7

3. AI вызывает activate_for_task("redis cache and github issue")
   → Orchestrator активирует: redis, github, context7
   → AI получает tools всех трех серверов (~5000 токенов)
   → Но только нужные! (вместо всех 100+ tools)

4. AI работает:
   → Использует context7 для получения docs по Redis
   → Использует redis tools для настройки кэша
   → Использует github tools для создания issue
```

---

## 🛠️ Новые/Улучшенные инструменты

### 1. `list_available_servers()` - УЛУЧШЕНО

**Текущее:** Хардкод в MCP_SERVER_REGISTRY

**Новое:** Автоматическое обнаружение из Docker MCP Toolkit

```python
@mcp.tool()
async def list_available_servers(
    include_inactive: bool = True,
    category_filter: str | None = None
) -> str:
    """
    List all available MCP servers discovered from Docker MCP Toolkit.
    
    **AUTO-DISCOVERED** - No manual configuration needed!
    
    Returns brief catalog WITHOUT tool details to minimize tokens.
    Use server_info() or activate_server() to get tool details.
    
    Args:
        include_inactive: Include inactive servers (default: True)
        category_filter: Filter by category (e.g., "database", "browser")
    
    Returns:
        Brief catalog: name, status, category, description, tool count
        ~200-500 tokens (instead of 15-20k!)
    """
```

**Формат ответа:**
```
📦 Available MCP Servers (12)

🗄️ Database (2)
  • redis (⚪) - Redis cache and data store
    ~15 tools | Requires: None
  • postgres (⚪) - PostgreSQL database access
    ~1 tool | Requires: None

🌐 Browser (1)
  • playwright (⚪) - Browser automation
    ~15 tools | Requires: None

📚 Documentation (1)
  • context7 (⚪) - Library documentation
    ~2 tools | Requires: None

🔧 Version Control (1)
  • github (⚪) - GitHub integration
    ~20 tools | Requires: OAuth

...
```

### 2. `server_info(server_name)` - НОВЫЙ

```python
@mcp.tool()
async def server_info(server_name: str) -> str:
    """
    Get detailed information about a specific server.
    
    Returns metadata WITHOUT activating the server.
    Use this to decide if you need a server before activating.
    
    Args:
        server_name: Server to get info about
    
    Returns:
        Detailed metadata: description, category, auth, tool count
        ~100-200 tokens
    """
```

### 3. `activate_server()` - УЛУЧШЕНО

**Новое поведение:**
- Автоматически получает tools после активации
- Возвращает список tools (только для активированного сервера)
- Автоматически активирует context7 для библиотек

```python
@mcp.tool()
async def activate_server(
    server_name: str,
    reason: str = "",
    auto_activate_docs: bool = True
) -> str:
    """
    Activate server and return its tools.
    
    After activation, tools become available through Docker MCP Gateway.
    
    Returns:
        Status + list of available tools (~1000-3000 tokens per server)
    """
```

### 4. `discover_servers()` - НОВЫЙ

```python
@mcp.tool()
async def discover_servers(force_refresh: bool = False) -> str:
    """
    Discover all MCP servers from Docker MCP Toolkit.
    
    Automatically called on startup, but can be called manually
    to refresh the server catalog.
    
    Args:
        force_refresh: Force re-discovery even if cached
    
    Returns:
        Discovery results
    """
```

### 5. `get_active_servers()` - УЛУЧШЕНО

**Новое:** Показывает tools только для активных серверов

```python
@mcp.tool()
async def get_active_servers(include_tools: bool = True) -> str:
    """
    Get list of active servers.
    
    Args:
        include_tools: Include tool lists (default: True)
                      Set False to minimize tokens
    
    Returns:
        Active servers with their tools (if include_tools=True)
    """
```

---

## 🏗️ Архитектура реализации

### 1. Автоматическое обнаружение серверов

```python
class ServerDiscovery:
    """Автоматическое обнаружение серверов из Docker MCP Toolkit"""
    
    async def discover_all_servers(self) -> dict[str, ServerMetadata]:
        """
        1. docker mcp server ls → список серверов
        2. Для каждого: docker mcp server inspect → метаданные
        3. docker mcp tools list --server <name> → количество tools
        4. Возвращает словарь метаданных
        """
    
    async def get_server_metadata(self, name: str) -> ServerMetadata:
        """Получить метаданные конкретного сервера"""
    
    async def get_server_tool_count(self, name: str) -> int:
        """Получить количество tools (БЕЗ деталей)"""
```

### 2. Кэширование метаданных

```python
@dataclass
class ServerMetadata:
    """Метаданные сервера (без tools)"""
    name: str
    description: str | None
    category: str  # Автоопределение или из конфига
    tool_count: int
    requires_auth: bool
    auth_type: str | None
    status: str  # "active" | "inactive"
    last_discovered: datetime

class ServerRegistry:
    """Реестр обнаруженных серверов"""
    
    def __init__(self):
        self.servers: dict[str, ServerMetadata] = {}
        self.last_discovery: datetime | None = None
        self.discovery_interval = timedelta(minutes=5)
    
    async def refresh(self, force: bool = False):
        """Обновить реестр из Docker MCP Toolkit"""
    
    def get_catalog(self, category_filter: str | None = None) -> list[ServerMetadata]:
        """Получить каталог для list_available_servers()"""
```

### 3. Умное определение категорий

```python
CATEGORY_KEYWORDS = {
    "database": ["redis", "postgres", "mysql", "mongodb", "sqlite"],
    "browser": ["playwright", "puppeteer", "selenium"],
    "documentation": ["context7", "docs", "readme"],
    "version_control": ["github", "gitlab", "bitbucket"],
    "networking": ["fetch", "http", "curl", "requests"],
    "system": ["desktop", "commander", "file", "shell"],
    "reasoning": ["thinking", "sequential", "planning"],
}

def auto_detect_category(server_name: str, description: str = "") -> str:
    """Автоматически определить категорию по названию/описанию"""
    name_lower = server_name.lower()
    desc_lower = description.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower or kw in desc_lower for kw in keywords):
            return category
    
    return "other"
```

### 4. Конфигурация для расширенных метаданных

```python
# config/servers.json (опционально)
{
  "servers": {
    "redis": {
      "category": "database",
      "description": "Redis cache and data store",
      "auto_activate_docs": true
    },
    "custom-server": {
      "category": "custom",
      "description": "My custom server"
    }
  },
  "categories": {
    "database": "🗄️ Database",
    "browser": "🌐 Browser",
    "documentation": "📚 Documentation"
  }
}
```

---

## 📊 Сравнение: Старое vs Новое

| Аспект | Старое (текущее) | Новое (предлагаемое) |
|--------|------------------|----------------------|
| **Обнаружение серверов** | Хардкод в коде | Автоматическое из Docker MCP Toolkit |
| **Токены при старте** | ~500 (только orchestrator) | ~500 (только orchestrator) |
| **Токены за каталог** | ~300 (хардкод) | ~300 (автообнаружение) |
| **Токены за tools** | Все сразу (15-20k) | Только активированные (1-5k) |
| **Добавление сервера** | Изменить код | Автоматически обнаруживается |
| **Синхронизация** | Ручная sync_state() | Автоматическая каждые 5 минут |
| **Категории** | Хардкод | Автоопределение + конфиг |
| **Метаданные** | Статические | Динамические из Docker MCP Toolkit |

---

## 🎯 Преимущества новой схемы

### 1. **Автоматическое обнаружение**
- ✅ Не нужно обновлять код при добавлении сервера
- ✅ Всегда актуальный список
- ✅ Работает с любыми серверами Docker MCP Toolkit

### 2. **Минимум токенов**
- ✅ При старте: только 8 инструментов orchestrator (~500 токенов)
- ✅ Каталог: только метаданные без tools (~300 токенов)
- ✅ Tools: только для активированных серверов (1-5k вместо 15-20k)

### 3. **Гибкость для AI**
- ✅ AI видит все доступные серверы
- ✅ AI сам выбирает что активировать
- ✅ AI может запросить детали перед активацией

### 4. **Умные рекомендации**
- ✅ activate_for_task() работает с любыми серверами
- ✅ Автоматическое определение категорий
- ✅ Автоматическая активация context7 для библиотек

---

## 🔧 Технические детали

### Команды Docker MCP CLI

```bash
# 1. Список всех серверов
docker mcp server ls
# Output:
# NAME              STATUS
# context7          disabled
# playwright        disabled
# redis             enabled
# ...

# 2. Метаданные сервера
docker mcp server inspect redis
# Output: JSON с описанием, конфигурацией, etc.

# 3. Количество tools (без деталей)
docker mcp tools list --server redis --count-only
# Или просто посчитать строки в полном списке

# 4. Список tools (только имена, без схем)
docker mcp tools list --server redis --names-only
```

### Структура данных

```python
@dataclass
class ServerMetadata:
    name: str
    description: str | None
    category: str
    tool_count: int
    requires_auth: bool
    auth_type: str | None
    status: str  # "enabled" | "disabled"
    last_discovered: datetime
    config_override: dict | None = None  # Из config/servers.json
```

### Периодическая синхронизация

```python
async def background_sync_task():
    """Фоновая задача синхронизации"""
    while True:
        await asyncio.sleep(300)  # Каждые 5 минут
        await registry.refresh(force=False)
```

---

## 🚀 План внедрения

### Фаза 1: Автоматическое обнаружение
1. Реализовать ServerDiscovery
2. Реализовать ServerRegistry с кэшированием
3. Обновить list_available_servers() для использования реестра

### Фаза 2: Улучшенные инструменты
1. Добавить server_info()
2. Улучшить activate_server() с авто-получением tools
3. Добавить discover_servers()

### Фаза 3: Умные функции
1. Автоопределение категорий
2. Улучшить activate_for_task()
3. Автоматическая синхронизация

### Фаза 4: Опциональная конфигурация
1. Поддержка config/servers.json
2. Переопределение метаданных через конфиг
3. Кастомные категории

---

## ❓ Вопросы для уточнения

1. **Частота синхронизации:** Как часто проверять новые серверы? (предлагаю: каждые 5 минут)

2. **Кэширование:** Хранить метаданные в памяти или в файле? (предлагаю: память + периодическая синхронизация)

3. **Конфигурация:** Нужен ли config/servers.json для переопределения метаданных? (опционально)

4. **Обратная совместимость:** Сохранить MCP_SERVER_REGISTRY как fallback? (да, для серверов не обнаруженных автоматически)

5. **Категории:** Полностью автоопределение или приоритет конфигу? (предлагаю: конфиг > автоопределение > "other")

---

## ✅ Итоговая схема

```
┌─────────────────────────────────────────────────────────┐
│  Docker MCP Toolkit                                      │
│  (Все MCP серверы установлены)                          │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼ (автоматическое обнаружение)
┌─────────────────────────────────────────────────────────┐
│  Docker MCP Orchestrator                                 │
│  - Обнаруживает все серверы                              │
│  - Кэширует метаданные (без tools)                      │
│  - Предоставляет краткий каталог AI                      │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  AI получает при старте:                                 │
│  - 8 инструментов orchestrator (~500 токенов)           │
│  - Краткий каталог серверов (~300 токенов)              │
│  ИТОГО: ~800 токенов (вместо 15-20k!)                  │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼ (AI выбирает и активирует)
┌─────────────────────────────────────────────────────────┐
│  AI активирует нужные серверы:                           │
│  - activate_server("redis")                              │
│  - activate_server("context7")                           │
│                                                          │
│  AI получает tools только активированных:               │
│  - Redis tools (~1500 токенов)                          │
│  - Context7 tools (~500 токенов)                        │
│  ИТОГО: ~2000 токенов (вместо 15-20k!)                  │
└─────────────────────────────────────────────────────────┘
```

**Экономия токенов: 90%+ при старте, 85%+ при работе!**
