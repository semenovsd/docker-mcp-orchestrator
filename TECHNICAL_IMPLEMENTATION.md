# Техническая реализация новой схемы

## 🏗️ Архитектура компонентов

### 1. ServerDiscovery - Автоматическое обнаружение

```python
"""
Модуль для автоматического обнаружения MCP серверов из Docker MCP Toolkit.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class ServerMetadata:
    """Метаданные сервера (без деталей tools)"""
    name: str
    description: str | None = None
    category: str = "other"
    tool_count: int = 0
    requires_auth: bool = False
    auth_type: str | None = None
    status: str = "disabled"  # "enabled" | "disabled"
    last_discovered: datetime | None = None
    config_override: dict[str, Any] | None = None  # Из config/servers.json


class ServerDiscovery:
    """Автоматическое обнаружение серверов из Docker MCP Toolkit"""
    
    def __init__(self):
        self.logger = logging.getLogger("discovery")
    
    async def discover_all_servers(self) -> dict[str, ServerMetadata]:
        """
        Обнаружить все доступные серверы из Docker MCP Toolkit.
        
        Returns:
            Словарь {server_name: ServerMetadata}
        """
        # 1. Получить список всех серверов
        servers_list = await self._list_servers()
        
        # 2. Для каждого сервера получить метаданные
        metadata_dict = {}
        for server_name in servers_list:
            try:
                metadata = await self._get_server_metadata(server_name)
                metadata_dict[server_name] = metadata
            except Exception as e:
                self.logger.warning(f"Failed to get metadata for {server_name}: {e}")
                # Fallback: минимальные метаданные
                metadata_dict[server_name] = ServerMetadata(
                    name=server_name,
                    status="unknown"
                )
        
        return metadata_dict
    
    async def _list_servers(self) -> list[str]:
        """Получить список всех серверов"""
        success, output = run_docker_mcp_command(["server", "ls"])
        
        if not success:
            self.logger.error(f"Failed to list servers: {output}")
            return []
        
        servers = []
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('NAME') and not line.startswith('-'):
                parts = line.split()
                if parts:
                    servers.append(parts[0])
        
        return servers
    
    async def _get_server_metadata(self, server_name: str) -> ServerMetadata:
        """Получить метаданные конкретного сервера"""
        # 1. Проверить статус
        status = await self._get_server_status(server_name)
        
        # 2. Получить inspect информацию
        inspect_data = await self._inspect_server(server_name)
        
        # 3. Получить количество tools (БЕЗ деталей)
        tool_count = await self._get_tool_count(server_name)
        
        # 4. Определить категорию
        category = self._detect_category(server_name, inspect_data.get("description", ""))
        
        # 5. Проверить аутентификацию
        requires_auth, auth_type = self._check_auth_requirements(inspect_data)
        
        return ServerMetadata(
            name=server_name,
            description=inspect_data.get("description"),
            category=category,
            tool_count=tool_count,
            requires_auth=requires_auth,
            auth_type=auth_type,
            status=status,
            last_discovered=datetime.now()
        )
    
    async def _get_server_status(self, server_name: str) -> str:
        """Проверить статус сервера (enabled/disabled)"""
        success, output = run_docker_mcp_command(["server", "ls"])
        if not success:
            return "unknown"
        
        for line in output.split('\n'):
            if server_name in line:
                if "enabled" in line.lower() or "active" in line.lower():
                    return "enabled"
                return "disabled"
        
        return "disabled"
    
    async def _inspect_server(self, server_name: str) -> dict:
        """Получить детальную информацию о сервере"""
        success, output = run_docker_mcp_command(
            ["server", "inspect", server_name]
        )
        
        if not success:
            return {}
        
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            # Парсинг текстового вывода
            return {"description": output[:200]}
    
    async def _get_tool_count(self, server_name: str) -> int:
        """Получить количество tools (БЕЗ деталей)"""
        success, output = run_docker_mcp_command(
            ["tools", "list", "--server", server_name]
        )
        
        if not success:
            return 0
        
        try:
            # Если JSON
            data = json.loads(output)
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and "tools" in data:
                return len(data["tools"])
        except json.JSONDecodeError:
            # Если текстовый вывод - считаем строки
            lines = [l for l in output.split('\n') 
                    if l.strip() and not l.startswith('TOOL') 
                    and not l.startswith('-')]
            return len(lines)
        
        return 0
    
    def _detect_category(self, server_name: str, description: str = "") -> str:
        """Автоматически определить категорию"""
        CATEGORY_KEYWORDS = {
            "database": ["redis", "postgres", "mysql", "mongodb", "sqlite", "db"],
            "browser": ["playwright", "puppeteer", "selenium", "browser"],
            "documentation": ["context7", "docs", "readme", "documentation"],
            "version_control": ["github", "gitlab", "bitbucket", "git"],
            "networking": ["fetch", "http", "curl", "requests", "api"],
            "system": ["desktop", "commander", "file", "shell", "command"],
            "reasoning": ["thinking", "sequential", "planning", "reason"],
        }
        
        name_lower = server_name.lower()
        desc_lower = description.lower()
        combined = f"{name_lower} {desc_lower}"
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return "other"
    
    def _check_auth_requirements(self, inspect_data: dict) -> tuple[bool, str | None]:
        """Проверить требования к аутентификации"""
        # Проверяем в inspect_data
        if "auth" in inspect_data or "authentication" in inspect_data:
            auth_info = inspect_data.get("auth") or inspect_data.get("authentication")
            if isinstance(auth_info, dict):
                auth_type = auth_info.get("type") or auth_info.get("method")
                return True, auth_type
            return True, "oauth"  # По умолчанию
        
        # Проверяем по известным серверам
        KNOWN_AUTH_SERVERS = {
            "github": "oauth",
            "gitlab": "oauth",
        }
        
        return False, None
```

### 2. ServerRegistry - Реестр и кэширование

```python
"""
Реестр обнаруженных серверов с кэшированием.
"""

from datetime import datetime, timedelta
from typing import Optional

class ServerRegistry:
    """Реестр серверов с автоматическим обновлением"""
    
    def __init__(self, discovery: ServerDiscovery):
        self.discovery = discovery
        self.servers: dict[str, ServerMetadata] = {}
        self.last_discovery: datetime | None = None
        self.discovery_interval = timedelta(minutes=5)
        self.config_overrides: dict[str, dict] = {}
        self._load_config_overrides()
    
    def _load_config_overrides(self):
        """Загрузить переопределения из config/servers.json (если есть)"""
        config_path = Path("config/servers.json")
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    self.config_overrides = config.get("servers", {})
            except Exception as e:
                logger.warning(f"Failed to load server config: {e}")
    
    async def refresh(self, force: bool = False) -> dict[str, ServerMetadata]:
        """
        Обновить реестр серверов.
        
        Args:
            force: Принудительное обновление даже если недавно обновляли
        
        Returns:
            Обновленный словарь серверов
        """
        now = datetime.now()
        
        # Проверяем нужно ли обновление
        if not force and self.last_discovery:
            if (now - self.last_discovery) < self.discovery_interval:
                logger.debug("Using cached server registry")
                return self.servers
        
        logger.info("Refreshing server registry...")
        
        # Обнаруживаем серверы
        discovered = await self.discovery.discover_all_servers()
        
        # Применяем переопределения из конфига
        for name, metadata in discovered.items():
            if name in self.config_overrides:
                override = self.config_overrides[name]
                if "category" in override:
                    metadata.category = override["category"]
                if "description" in override:
                    metadata.description = override["description"]
                metadata.config_override = override
        
        self.servers = discovered
        self.last_discovery = now
        
        logger.info(f"Discovered {len(self.servers)} servers")
        return self.servers
    
    def get_catalog(
        self, 
        category_filter: Optional[str] = None,
        include_inactive: bool = True
    ) -> list[ServerMetadata]:
        """
        Получить каталог серверов для list_available_servers().
        
        Args:
            category_filter: Фильтр по категории
            include_inactive: Включать неактивные серверы
        
        Returns:
            Список метаданных серверов
        """
        servers = list(self.servers.values())
        
        # Фильтр по категории
        if category_filter:
            servers = [s for s in servers if s.category == category_filter]
        
        # Фильтр по статусу
        if not include_inactive:
            servers = [s for s in servers if s.status == "enabled"]
        
        return sorted(servers, key=lambda s: (s.category, s.name))
    
    def get_server(self, name: str) -> ServerMetadata | None:
        """Получить метаданные конкретного сервера"""
        return self.servers.get(name)
    
    def get_by_category(self, category: str) -> list[ServerMetadata]:
        """Получить все серверы категории"""
        return [s for s in self.servers.values() if s.category == category]
    
    def get_categories(self) -> set[str]:
        """Получить все категории"""
        return {s.category for s in self.servers.values()}
```

### 3. Обновленные инструменты

```python
# Глобальный реестр
registry = ServerRegistry(ServerDiscovery())

# При старте - автоматическое обнаружение
async def initialize_registry():
    """Инициализация реестра при старте"""
    await registry.refresh(force=True)

@mcp.tool()
async def list_available_servers(
    include_inactive: bool = True,
    category_filter: str | None = None
) -> str:
    """
    List all available MCP servers discovered from Docker MCP Toolkit.
    
    **AUTO-DISCOVERED** - No manual configuration needed!
    Returns brief catalog WITHOUT tool details to minimize tokens.
    
    Use server_info() to get details, or activate_server() to get tools.
    
    Args:
        include_inactive: Include inactive servers (default: True)
        category_filter: Filter by category (e.g., "database", "browser")
    
    Returns:
        Brief catalog: name, status, category, description, tool count
        ~200-500 tokens (instead of 15-20k!)
    """
    # Обновляем реестр если нужно
    await registry.refresh(force=False)
    
    # Получаем каталог
    servers = registry.get_catalog(
        category_filter=category_filter,
        include_inactive=include_inactive
    )
    
    if not servers:
        return "ℹ️ No servers found. Check Docker MCP Toolkit configuration."
    
    # Группируем по категориям
    categories: dict[str, list[ServerMetadata]] = {}
    for server in servers:
        if server.category not in categories:
            categories[server.category] = []
        categories[server.category].append(server)
    
    # Формируем краткий каталог
    result = [f"# 📦 Available MCP Servers ({len(servers)})\n"]
    
    # Эмодзи для категорий
    CATEGORY_EMOJIS = {
        "database": "🗄️",
        "browser": "🌐",
        "documentation": "📚",
        "version_control": "🔧",
        "networking": "🌍",
        "system": "💻",
        "reasoning": "🧠",
        "other": "📦",
    }
    
    for category, category_servers in sorted(categories.items()):
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        result.append(f"\n## {emoji} {category.replace('_', ' ').title()} ({len(category_servers)})")
        
        for server in category_servers:
            status_emoji = "🟢" if server.status == "enabled" else "⚪"
            auth_badge = f" 🔐 {server.auth_type}" if server.requires_auth else ""
            
            result.append(f"  • **{server.name}** ({status_emoji}){auth_badge}")
            
            if server.description:
                result.append(f"    {server.description[:80]}")
            
            result.append(f"    ~{server.tool_count} tools")
            result.append("")
    
    result.append(f"\n---\n**Total**: {len(servers)} servers")
    result.append(f"**Active**: {sum(1 for s in servers if s.status == 'enabled')} servers")
    result.append("\n💡 Use `server_info(name)` for details, or `activate_server(name)` to get tools.")
    
    return "\n".join(result)


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
    await registry.refresh(force=False)
    
    server = registry.get_server(server_name)
    if not server:
        available = ", ".join(sorted(registry.servers.keys()))
        return (
            f"❌ Server '{server_name}' not found.\n\n"
            f"**Available servers**: {available}\n\n"
            f"Use `list_available_servers()` to see all servers."
        )
    
    lines = [
        f"# {server_name}",
        "",
        f"**Status**: {'🟢 Active' if server.status == 'enabled' else '⚪ Inactive'}",
        f"**Category**: {server.category}",
        f"**Tool Count**: ~{server.tool_count} tools",
    ]
    
    if server.description:
        lines.append(f"\n**Description**:\n{server.description}")
    
    if server.requires_auth:
        lines.append(f"\n**Authentication**: 🔐 {server.auth_type or 'Required'}")
        lines.append("Configure in Docker MCP Toolkit before activation.")
    else:
        lines.append("\n**Authentication**: None required")
    
    lines.append(f"\n**Last Discovered**: {server.last_discovered or 'Never'}")
    
    lines.append("\n---")
    lines.append("💡 Use `activate_server(\"{server_name}\")` to activate and get tools.")
    
    return "\n".join(lines)


@mcp.tool()
async def discover_servers(force_refresh: bool = False) -> str:
    """
    Discover all MCP servers from Docker MCP Toolkit.
    
    Automatically called on startup, but can be called manually
    to refresh the server catalog.
    
    Args:
        force_refresh: Force re-discovery even if recently refreshed
    
    Returns:
        Discovery results
    """
    before_count = len(registry.servers)
    
    discovered = await registry.refresh(force=force_refresh)
    
    after_count = len(discovered)
    new_servers = set(discovered.keys()) - set(registry.servers.keys()) if before_count > 0 else set()
    
    lines = [
        "# 🔍 Server Discovery",
        "",
        f"**Discovered**: {after_count} servers",
    ]
    
    if new_servers:
        lines.append(f"**New servers**: {', '.join(sorted(new_servers))}")
    
    if before_count > 0:
        lines.append(f"**Previous count**: {before_count}")
    
    lines.append(f"\n**Last discovery**: {registry.last_discovery}")
    lines.append("\n💡 Use `list_available_servers()` to see the catalog.")
    
    return "\n".join(lines)
```

### 4. Фоновая синхронизация

```python
async def background_sync_task():
    """Фоновая задача периодической синхронизации"""
    while True:
        try:
            await asyncio.sleep(300)  # Каждые 5 минут
            await registry.refresh(force=False)
            logger.debug("Background sync completed")
        except Exception as e:
            logger.error(f"Background sync failed: {e}")

# В main():
async def main():
    # Инициализация
    await initialize_registry()
    
    # Запуск фоновой задачи (если поддерживается)
    # asyncio.create_task(background_sync_task())
    
    # Запуск MCP сервера
    mcp.run()
```

---

## 📝 Конфигурационный файл (опционально)

### config/servers.json

```json
{
  "servers": {
    "redis": {
      "category": "database",
      "description": "Redis cache and data store operations",
      "auto_activate_docs": true
    },
    "custom-server": {
      "category": "custom",
      "description": "My custom MCP server"
    }
  },
  "categories": {
    "database": "🗄️ Database",
    "browser": "🌐 Browser",
    "documentation": "📚 Documentation",
    "version_control": "🔧 Version Control",
    "networking": "🌍 Networking",
    "system": "💻 System",
    "reasoning": "🧠 Reasoning",
    "other": "📦 Other"
  },
  "discovery": {
    "interval_minutes": 5,
    "auto_refresh": true
  }
}
```

---

## 🔄 Workflow сравнение

### Старый workflow

```
1. AI стартует
   → Видит 8 инструментов orchestrator
   → Видит хардкод список серверов (если вызвал list_available_servers)
   → НЕ ЗНАЕТ про новые серверы в Docker MCP Toolkit

2. AI активирует сервер
   → activate_server("redis")
   → Получает tools redis
   → Работает
```

### Новый workflow

```
1. Orchestrator стартует
   → Автоматически обнаруживает все серверы из Docker MCP Toolkit
   → Кэширует метаданные (без tools)
   → Готов к работе

2. AI стартует
   → Видит 8 инструментов orchestrator (~500 токенов)
   → Вызывает list_available_servers()
   → Получает КРАТКИЙ каталог всех серверов (~300 токенов)
   → ВСЕГО: ~800 токенов (вместо 15-20k!)

3. AI выбирает нужные серверы
   → Может вызвать server_info("redis") для деталей (~100 токенов)
   → Вызывает activate_server("redis")
   → Получает tools только redis (~1500 токенов)
   → Работает

4. Фоновая синхронизация
   → Каждые 5 минут проверяет новые серверы
   → Обновляет каталог автоматически
```

---

## ✅ Преимущества реализации

1. **Автоматическое обнаружение** - не нужно обновлять код
2. **Минимум токенов** - только метаданные без tools
3. **Актуальность** - всегда знает про все серверы
4. **Гибкость** - конфиг для переопределений
5. **Производительность** - кэширование + периодическая синхронизация

---

## 🚀 План внедрения

### Шаг 1: ServerDiscovery (1-2 часа)
- Реализовать класс ServerDiscovery
- Методы для обнаружения и получения метаданных
- Тесты

### Шаг 2: ServerRegistry (1 час)
- Реализовать класс ServerRegistry
- Кэширование и обновление
- Интеграция с ServerDiscovery

### Шаг 3: Обновить инструменты (2 часа)
- Обновить list_available_servers()
- Добавить server_info()
- Добавить discover_servers()

### Шаг 4: Инициализация (30 мин)
- Автоматическое обнаружение при старте
- Фоновая синхронизация (опционально)

### Шаг 5: Конфигурация (1 час)
- Поддержка config/servers.json
- Переопределение метаданных

### Шаг 6: Тестирование (1-2 часа)
- Тесты для всех компонентов
- Интеграционные тесты
- Проверка экономии токенов

**Итого: 6-8 часов работы**
