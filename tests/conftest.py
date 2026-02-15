# conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_bot():
    """Мок объекта Bot."""
    bot = AsyncMock()
    bot.me = AsyncMock(return_value=MagicMock(id=123456789, username="test_bot"))
    return bot

@pytest.fixture
def mock_dispatcher():
    """Мок Dispatcher."""
    dp = AsyncMock()
    dp.storage = AsyncMock()
    return dp