# Техническая реализация гибридного решения

## 🏗️ Структура проекта

```
src/mcp_orchestrator/
├── __init__.py
├── server.py                    # Основной MCP сервер
├── discovery.py                 # Автоматическое обнаружение
├── registry.py                  # Реестр серверов
├── analyzer.py                  # Анализ задач
├── router.py                    # Умная маршрутизация
├── profiles.py                  # Профили серверов
├── monitor.py                   # Мониторинг использования
├── cache.py                     # Кэширование
└── utils.py                     # Утилиты
```

---

## 📦 Компоненты

### 1. discovery.py - Автоматическое обнаружение

```python
"""
Автоматическое обнаружение MCP серверов из Docker MCP Toolkit.
"""

import asyncio
import json
import subprocess
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("discovery")


@dataclass
class ServerMetadata:
    """Метаданные сервера (без деталей tools)"""
    name: str
    description: Optional[str] = None
    category: str = "other"
    tool_count: int = 0
    requires_auth: bool = False
    auth_type: Optional[str] = None
    status: str = "disabled"
    last_discovered: Optional[datetime] = None
    config_override: Optional[dict[str, Any]] = None


class ServerDiscovery:
    """Автоматическое обнаружение серверов"""
    
    CATEGORY_KEYWORDS = {
        "database": ["redis", "postgres", "mysql", "mongodb", "sqlite", "db"],
        "browser": ["playwright", "puppeteer", "selenium", "browser"],
        "documentation": ["context7", "docs", "readme", "documentation"],
        "version_control": ["github", "gitlab", "bitbucket", "git"],
        "networking": ["fetch", "http", "curl", "requests", "api"],
        "system": ["desktop", "commander", "file", "shell", "command"],
        "reasoning": ["thinking", "sequential", "planning", "reason"],
    }
    
    def __init__(self):
        self.logger = logger
    
    async def discover_all_servers(self) -> dict[str, ServerMetadata]:
        """Обнаружить все доступные серверы"""
        servers_list = await self._list_servers()
        
        metadata_dict = {}
        for server_name in servers_list:
            try:
                metadata = await self._get_server_metadata(server_name)
                metadata_dict[server_name] = metadata
            except Exception as e:
                self.logger.warning(f"Failed to get metadata for {server_name}: {e}")
                metadata_dict[server_name] = ServerMetadata(
                    name=server_name,
                    status="unknown"
                )
        
        return metadata_dict
    
    async def _list_servers(self) -> list[str]:
        """Получить список всех серверов"""
        from .server import run_docker_mcp_command
        
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
        from .server import run_docker_mcp_command
        
        status = await self._get_server_status(server_name)
        inspect_data = await self._inspect_server(server_name)
        tool_count = await self._get_tool_count(server_name)
        category = self._detect_category(server_name, inspect_data.get("description", ""))
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
        """Проверить статус сервера"""
        from .server import run_docker_mcp_command
        
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
        from .server import run_docker_mcp_command
        
        success, output = run_docker_mcp_command(
            ["server", "inspect", server_name]
        )
        
        if not success:
            return {}
        
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"description": output[:200]}
    
    async def _get_tool_count(self, server_name: str) -> int:
        """Получить количество tools (БЕЗ деталей)"""
        from .server import run_docker_mcp_command
        
        success, output = run_docker_mcp_command(
            ["tools", "list", "--server", server_name]
        )
        
        if not success:
            return 0
        
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and "tools" in data:
                return len(data["tools"])
        except json.JSONDecodeError:
            lines = [l for l in output.split('\n') 
                    if l.strip() and not l.startswith('TOOL') 
                    and not l.startswith('-')]
            return len(lines)
        
        return 0
    
    def _detect_category(self, server_name: str, description: str = "") -> str:
        """Автоматически определить категорию"""
        name_lower = server_name.lower()
        desc_lower = description.lower()
        combined = f"{name_lower} {desc_lower}"
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                return category
        
        return "other"
    
    def _check_auth_requirements(self, inspect_data: dict) -> tuple[bool, Optional[str]]:
        """Проверить требования к аутентификации"""
        if "auth" in inspect_data or "authentication" in inspect_data:
            auth_info = inspect_data.get("auth") or inspect_data.get("authentication")
            if isinstance(auth_info, dict):
                auth_type = auth_info.get("type") or auth_info.get("method")
                return True, auth_type
            return True, "oauth"
        
        KNOWN_AUTH_SERVERS = {
            "github": "oauth",
            "gitlab": "oauth",
        }
        
        return False, None
```

### 2. analyzer.py - Анализ задач

```python
"""
Умный анализ задач для определения нужных серверов.
"""

from dataclasses import dataclass
from typing import list, Optional
import re


@dataclass
class TaskAnalysis:
    """Результат анализа задачи"""
    required_servers: list[str]
    recommended_servers: list[str]
    activation_order: list[str]
    estimated_tokens: int
    confidence: float  # 0.0 - 1.0


class SmartTaskAnalyzer:
    """Умный анализ задач"""
    
    # Ключевые слова для серверов
    SERVER_KEYWORDS = {
        "context7": ["documentation", "docs", "api reference", "library", 
                     "framework", "package", "sdk", "readme"],
        "playwright": ["browser", "screenshot", "scrape", "website", "click", 
                       "form", "web page", "navigate", "automation", "selenium"],
        "github": ["github", "repository", "repo", "issue", "pull request", 
                   "pr", "commit", "code search", "gist", "git"],
        "fetch": ["http", "api", "fetch", "download", "request", "url", "curl"],
        "desktop-commander": ["file", "folder", "directory", "command", 
                              "execute", "process", "terminal", "shell"],
        "postgres": ["database", "sql", "query", "postgres", "postgresql", 
                     "table", "db", "data"],
        "redis": ["cache", "redis", "session", "pub/sub", "key-value", "storage"],
        "sequential-thinking": ["analyze", "think", "reason", "plan", 
                               "complex", "multi-step", "decision"],
    }
    
    # Зависимости серверов
    SERVER_DEPENDENCIES = {
        "redis": ["context7"],
        "postgres": ["context7"],
        "playwright": ["context7"],
        "github": ["context7"],
        "fetch": ["context7"],
    }
    
    def __init__(self):
        pass
    
    def analyze_task(self, task_description: str) -> TaskAnalysis:
        """
        Анализирует задачу и определяет нужные серверы.
        
        Args:
            task_description: Описание задачи
        
        Returns:
            TaskAnalysis с рекомендациями
        """
        task_lower = task_description.lower()
        
        # Находим упомянутые серверы
        mentioned_servers = set()
        for server, keywords in self.SERVER_KEYWORDS.items():
            for kw in keywords:
                if kw in task_lower:
                    mentioned_servers.add(server)
                    break
        
        # Определяем обязательные серверы
        required = list(mentioned_servers)
        
        # Добавляем зависимости
        recommended = []
        for server in required:
            deps = self.SERVER_DEPENDENCIES.get(server, [])
            for dep in deps:
                if dep not in required and dep not in recommended:
                    recommended.append(dep)
        
        # Если упоминается библиотека/фреймворк, добавляем context7
        library_keywords = ["library", "framework", "api", "sdk", "package"]
        if any(kw in task_lower for kw in library_keywords):
            if "context7" not in required and "context7" not in recommended:
                recommended.append("context7")
        
        # Оптимизируем порядок активации
        activation_order = self._optimize_order(required + recommended)
        
        # Оцениваем токены
        estimated_tokens = self._estimate_tokens(required + recommended)
        
        # Уверенность в анализе
        confidence = self._calculate_confidence(task_lower, required)
        
        return TaskAnalysis(
            required_servers=required,
            recommended_servers=recommended,
            activation_order=activation_order,
            estimated_tokens=estimated_tokens,
            confidence=confidence
        )
    
    def _optimize_order(self, servers: list[str]) -> list[str]:
        """Оптимизирует порядок активации"""
        # Сначала зависимости (context7), потом основные серверы
        deps = [s for s in servers if s == "context7"]
        main = [s for s in servers if s != "context7"]
        return deps + main
    
    def _estimate_tokens(self, servers: list[str]) -> int:
        """Оценивает количество токенов"""
        # Примерная оценка: ~1000 токенов на сервер
        return len(servers) * 1000
    
    def _calculate_confidence(self, task: str, servers: list[str]) -> float:
        """Вычисляет уверенность в анализе"""
        if not servers:
            return 0.0
        
        # Чем больше ключевых слов найдено, тем выше уверенность
        matches = 0
        total_keywords = 0
        
        for server in servers:
            keywords = self.SERVER_KEYWORDS.get(server, [])
            total_keywords += len(keywords)
            for kw in keywords:
                if kw in task:
                    matches += 1
        
        if total_keywords == 0:
            return 0.5  # Средняя уверенность
        
        return min(1.0, matches / total_keywords * 2)  # Нормализуем
```

### 3. profiles.py - Профили серверов

```python
"""
Профили серверов для типичных задач.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerProfile:
    """Профиль серверов"""
    name: str
    description: str
    servers: list[str]
    auto_activate: bool = True
    estimated_tokens: int = 0


SERVER_PROFILES: dict[str, ServerProfile] = {
    "web-development": ServerProfile(
        name="web-development",
        description="Web development tasks: browser automation, GitHub, HTTP",
        servers=["playwright", "github", "context7", "fetch"],
        auto_activate=True,
        estimated_tokens=4000
    ),
    "data-science": ServerProfile(
        name="data-science",
        description="Data analysis: databases, caching, documentation",
        servers=["postgres", "redis", "context7"],
        auto_activate=True,
        estimated_tokens=3000
    ),
    "documentation": ServerProfile(
        name="documentation",
        description="Library documentation lookup",
        servers=["context7"],
        auto_activate=True,
        estimated_tokens=500
    ),
    "full-stack": ServerProfile(
        name="full-stack",
        description="Full stack development: all tools",
        servers=["playwright", "github", "postgres", "redis", 
                "context7", "fetch", "desktop-commander"],
        auto_activate=False,  # Требует подтверждения
        estimated_tokens=8000
    ),
    "database": ServerProfile(
        name="database",
        description="Database operations: PostgreSQL and Redis",
        servers=["postgres", "redis", "context7"],
        auto_activate=True,
        estimated_tokens=3000
    ),
}


def find_matching_profile(task_description: str) -> Optional[ServerProfile]:
    """Найти подходящий профиль для задачи"""
    task_lower = task_description.lower()
    
    profile_keywords = {
        "web-development": ["web", "website", "browser", "frontend", "ui"],
        "data-science": ["data", "analysis", "database", "sql", "query"],
        "documentation": ["documentation", "docs", "api", "reference"],
        "full-stack": ["full stack", "fullstack", "complete", "all"],
        "database": ["database", "db", "sql", "postgres", "redis"],
    }
    
    for profile_name, keywords in profile_keywords.items():
        if any(kw in task_lower for kw in keywords):
            return SERVER_PROFILES.get(profile_name)
    
    return None


def get_all_profiles() -> list[ServerProfile]:
    """Получить все профили"""
    return list(SERVER_PROFILES.values())
```

### 4. monitor.py - Мониторинг использования

```python
"""
Мониторинг использования серверов.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import dict, Optional
from collections import defaultdict


@dataclass
class ServerUsage:
    """Использование сервера"""
    last_used: datetime
    access_count: int = 0
    tool_usage: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class UsageMonitor:
    """Мониторинг использования серверов"""
    
    def __init__(self, idle_timeout_minutes: int = 10):
        self.idle_timeout = timedelta(minutes=idle_timeout_minutes)
        self.usage: dict[str, ServerUsage] = {}
    
    def track_activation(self, server_name: str):
        """Отслеживает активацию сервера"""
        now = datetime.now()
        if server_name not in self.usage:
            self.usage[server_name] = ServerUsage(last_used=now)
        else:
            self.usage[server_name].last_used = now
    
    def track_tool_usage(self, server_name: str, tool_name: str):
        """Отслеживает использование инструмента"""
        now = datetime.now()
        if server_name not in self.usage:
            self.usage[server_name] = ServerUsage(last_used=now)
        
        usage = self.usage[server_name]
        usage.last_used = now
        usage.access_count += 1
        usage.tool_usage[tool_name] += 1
    
    def get_usage_stats(self) -> dict[str, int]:
        """Получить статистику использования"""
        return {
            name: usage.access_count
            for name, usage in self.usage.items()
        }
    
    def recommend_deactivation(self, active_servers: set[str]) -> list[str]:
        """Рекомендует серверы для деактивации"""
        now = datetime.now()
        recommendations = []
        
        for server in active_servers:
            usage = self.usage.get(server)
            if usage:
                idle_time = now - usage.last_used
                if idle_time > self.idle_timeout:
                    recommendations.append(server)
            else:
                # Сервер активирован, но не использовался
                recommendations.append(server)
        
        return recommendations
    
    def get_server_stats(self, server_name: str) -> Optional[ServerUsage]:
        """Получить статистику конкретного сервера"""
        return self.usage.get(server_name)
```

### 5. Обновленный server.py - Интеграция всех компонентов

```python
# В начале файла добавить импорты
from .discovery import ServerDiscovery, ServerMetadata
from .registry import ServerRegistry
from .analyzer import SmartTaskAnalyzer
from .profiles import find_matching_profile, get_all_profiles
from .monitor import UsageMonitor

# Глобальные объекты
discovery = ServerDiscovery()
registry = ServerRegistry(discovery)
task_analyzer = SmartTaskAnalyzer()
usage_monitor = UsageMonitor()

# Обновить activate_for_task
@mcp.tool()
async def activate_for_task(
    task_description: str,
    auto_activate_deps: bool = True,
    use_profiles: bool = True
) -> str:
    """
    Умная активация серверов для задачи.
    
    **Улучшения:**
    - Анализирует задачу с помощью NLP
    - Определяет оптимальный набор серверов
    - Использует профили для групповой активации
    - Оптимизирует порядок активации
    - Автоматически активирует зависимости
    
    Args:
        task_description: Описание задачи
        auto_activate_deps: Автоматически активировать зависимости
        use_profiles: Использовать предустановленные профили
    
    Returns:
        Результаты активации с рекомендациями
    """
    # 1. Проверка профилей
    if use_profiles:
        matching_profile = find_matching_profile(task_description)
        if matching_profile and matching_profile.auto_activate:
            return await activate_profile(matching_profile.name)
    
    # 2. Анализ задачи
    analysis = task_analyzer.analyze_task(task_description)
    
    if not analysis.required_servers and not analysis.recommended_servers:
        return (
            "🤔 No servers detected for this task.\n\n"
            "Use `list_available_servers()` to see options, or be more "
            "specific (e.g., 'browser', 'github', 'database')."
        )
    
    # 3. Активация серверов
    all_servers = analysis.required_servers + analysis.recommended_servers
    activation_order = analysis.activation_order
    
    activated = []
    failed = []
    
    for server in activation_order:
        if server in state.active_servers:
            continue
        
        result = await activate_server(server, auto_activate_deps=auto_activate_deps)
        if "✅" in result:
            activated.append(server)
            usage_monitor.track_activation(server)
        else:
            failed.append(server)
    
    # 4. Формирование результата
    lines = [
        f"# 🔍 Task: {task_description[:80]}{'...' if len(task_description) > 80 else ''}",
        "",
        f"**Confidence**: {analysis.confidence:.0%}",
        f"**Estimated tokens**: ~{analysis.estimated_tokens}",
        "",
        "## Activation Results:",
    ]
    
    if activated:
        lines.append(f"✅ **Activated**: {', '.join(activated)}")
    
    if failed:
        lines.append(f"❌ **Failed**: {', '.join(failed)}")
    
    if analysis.recommended_servers:
        lines.append(f"\n💡 **Recommended**: {', '.join(analysis.recommended_servers)}")
    
    lines.append(f"\n📌 Tools are now available via MCP gateway.")
    
    return "\n".join(lines)

# Добавить новые инструменты
@mcp.tool()
async def activate_profile(profile_name: str) -> str:
    """Активировать предустановленный профиль серверов"""
    from .profiles import SERVER_PROFILES
    
    if profile_name not in SERVER_PROFILES:
        available = ", ".join(SERVER_PROFILES.keys())
        return f"❌ Unknown profile: {profile_name}\n\nAvailable: {available}"
    
    profile = SERVER_PROFILES[profile_name]
    servers = profile.servers
    
    activated = []
    for server in servers:
        if server not in state.active_servers:
            result = await activate_server(server)
            if "✅" in result:
                activated.append(server)
                usage_monitor.track_activation(server)
    
    return f"""
    ✅ Profile '{profile_name}' activated
    
    **Description**: {profile.description}
    **Servers activated**: {', '.join(activated)}
    **Estimated tokens**: ~{profile.estimated_tokens}
    """

@mcp.tool()
async def get_recommendations(task_description: str | None = None) -> str:
    """Получить рекомендации по серверам"""
    if task_description:
        analysis = task_analyzer.analyze_task(task_description)
        
        return f"""
        # 🎯 Recommendations for: {task_description[:60]}
        
        **Required servers:**
        {', '.join(analysis.required_servers) if analysis.required_servers else 'None'}
        
        **Recommended servers:**
        {', '.join(analysis.recommended_servers) if analysis.recommended_servers else 'None'}
        
        **Estimated tokens:** ~{analysis.estimated_tokens}
        **Confidence:** {analysis.confidence:.0%}
        
        **Activation order:**
        {' → '.join(analysis.activation_order)}
        """
    else:
        stats = usage_monitor.get_usage_stats()
        popular = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return f"""
        # 📊 Popular Server Combinations
        
        Based on usage statistics:
        {chr(10).join(f'  • {name}: {count} uses' for name, count in popular)}
        """

@mcp.tool()
async def monitor_usage(show_recommendations: bool = True) -> str:
    """Показать статистику использования"""
    stats = usage_monitor.get_usage_stats()
    active = state.active_servers
    
    lines = [
        "# 📊 Usage Statistics",
        "",
        f"**Active servers**: {len(active)}",
        f"**Total tools loaded**: {sum(len(state.server_tools_cache.get(s, [])) for s in active)}",
        "",
        "## Server Usage:",
    ]
    
    for server, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        status = "🟢" if server in active else "⚪"
        lines.append(f"  {status} **{server}**: {count} uses")
    
    if show_recommendations:
        recommendations = usage_monitor.recommend_deactivation(active)
        if recommendations:
            lines.append("\n## 💡 Recommendations:")
            lines.append("Consider deactivating (unused >10min):")
            for server in recommendations:
                lines.append(f"  - {server}")
    
    return "\n".join(lines)

@mcp.tool()
async def optimize_servers(keep_active: list[str] | None = None) -> str:
    """Оптимизировать набор активных серверов"""
    recommendations = usage_monitor.recommend_deactivation(state.active_servers)
    
    if keep_active:
        recommendations = [s for s in recommendations if s not in keep_active]
    
    if not recommendations:
        return "ℹ️ No servers to optimize. All active servers are in use."
    
    deactivated = []
    for server in recommendations:
        result = await deactivate_server(server)
        if "✅" in result:
            deactivated.append(server)
    
    current_tokens = sum(
        len(state.server_tools_cache.get(s, [])) * 100 
        for s in state.active_servers
    )
    
    return f"""
    # ⚡ Optimization Complete
    
    **Deactivated**: {', '.join(deactivated)}
    **Current active**: {len(state.active_servers)} servers
    **Estimated tokens**: ~{current_tokens}
    """
```

---

## 🔄 Инициализация

```python
# В main() добавить
async def initialize():
    """Инициализация всех компонентов"""
    logger.info("Initializing Smart MCP Orchestrator...")
    
    # 1. Обнаружение серверов
    await registry.refresh(force=True)
    logger.info(f"Discovered {len(registry.servers)} servers")
    
    # 2. Синхронизация состояния
    enabled = get_enabled_servers()
    state.active_servers = set(enabled) & set(registry.servers.keys())
    
    if state.active_servers:
        logger.info(f"Found active: {state.active_servers}")
        for server in state.active_servers:
            state.server_tools_cache[server] = get_server_tools(server)
            usage_monitor.track_activation(server)
    
    logger.info("Ready!")

def main():
    """Main entry point"""
    asyncio.run(initialize())
    mcp.run()
```

---

## ✅ Итоговая архитектура

```
Smart MCP Orchestrator
├── ServerDiscovery (автоматическое обнаружение)
├── ServerRegistry (кэширование метаданных)
├── SmartTaskAnalyzer (анализ задач)
├── ServerProfiles (профили для типичных задач)
├── UsageMonitor (мониторинг использования)
└── MCP Tools (умные инструменты)
    ├── list_available_servers() - краткий каталог
    ├── activate_for_task() - умная активация
    ├── activate_profile() - профили
    ├── get_recommendations() - рекомендации
    ├── monitor_usage() - мониторинг
    └── optimize_servers() - оптимизация
```

**Полная автоматизация + умные рекомендации + мониторинг = Senior AI Engineer решение!** 🚀
