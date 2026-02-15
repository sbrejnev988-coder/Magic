#!/usr/bin/env python3
"""
Тестовая проверка основных импортов и конфигурации бота.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Проверка импортов основных модулей."""
    print("🔍 Проверка импортов...")
    try:
        from bot.config import settings
        print("✅ bot.config.settings загружен")
    except Exception as e:
        print(f"❌ Ошибка загрузки settings: {e}")
        return False
    
    try:
        from bot.models import Base, UserSettings, Order, Consultation, HybridDraft, PredictionHistory
        print("✅ Модели загружены")
    except Exception as e:
        print(f"❌ Ошибка загрузки моделей: {e}")
        return False
    
    try:
        from bot.services.llm import LLMService
        print("✅ LLMService загружен")
    except Exception as e:
        print(f"⚠️  LLMService не загружен (возможно, требует API ключи): {e}")
    
    try:
        from bot.handlers.start import start_command
        print("✅ Хэндлеры загружены")
    except Exception as e:
        print(f"⚠️  Хэндлеры не загружены: {e}")
    
    return True

def test_config():
    """Проверка конфигурации."""
    print("\n🔧 Проверка конфигурации...")
    from bot.config import settings
    print(f"   Database URL: {'установлен' if settings.database.url else 'не установлен'}")
    print(f"   Telegram admin: {settings.telegram.admin_user_id}")
    print(f"   Redis URL: {settings.redis.url}")
    print(f"   Rate limit: {settings.rate_limit}")
    return True

if __name__ == "__main__":
    print("🧪 Тест работоспособности MysticBot")
    if test_imports() and test_config():
        print("\n✅ Все основные компоненты загружаются без ошибок.")
        print("   Примечание: для полного запуска бота требуется BOT_TOKEN в .env")
    else:
        print("\n❌ Обнаружены ошибки при загрузке компонентов.")
        sys.exit(1)