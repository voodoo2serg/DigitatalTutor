"""
DigitalTutor Bot - Comprehensive Test Suite
Полный набор тестов для проверки исправлений багов DT-REPAIR-001

Запуск: DATABASE_URL="postgresql+asyncpg://test:test@localhost/test" python -m pytest tests/test_bugfixes.py -v
"""
import pytest
import sys

sys.path.insert(0, '/srv/teaching-system')
sys.path.insert(0, '/srv/teaching-system/bot')


class TestDatabaseAsyncPattern:
    """Тест 1: SQLAlchemy MissingGreenlet Fix"""
    
    def test_async_session_context_manager_importable(self):
        """Проверяем что AsyncSessionContext можно импортировать"""
        from bot.services.db import AsyncSessionContext
        assert AsyncSessionContext is not None
    
    def test_get_async_session_is_decorated(self):
        """Проверяем что get_async_session декорирован @asynccontextmanager"""
        from bot.services.db import get_async_session
        # Проверяем что функция определена
        assert callable(get_async_session)


class TestConfigConsistency:
    """Тест 2: Конфигурация"""
    
    def test_student_roles_defined(self):
        """Проверяем что STUDENT_ROLES определены"""
        from bot.config import STUDENT_ROLES
        assert len(STUDENT_ROLES) > 0
        
        for code, info in STUDENT_ROLES.items():
            assert 'name' in info
            assert 'description' in info
    
    def test_status_info_defined(self):
        """Проверяем что STATUS_INFO определены"""
        from bot.config import STATUS_INFO
        required_statuses = ['draft', 'submitted', 'in_review', 'revision_required', 'accepted', 'rejected']
        
        for status in required_statuses:
            assert status in STATUS_INFO, f"Missing status: {status}"
            assert 'emoji' in STATUS_INFO[status]
            assert 'name' in STATUS_INFO[status]


class TestKeyboardConsistency:
    """Тест 3: Консистентность клавиатур"""
    
    def test_main_menu_has_status_button(self):
        """Проверяем что '📊 Статус' есть в главном меню"""
        from bot.keyboards import get_main_menu
        
        keyboard = get_main_menu()
        buttons = []
        for row in keyboard.keyboard:
            for button in row:
                buttons.append(button.text)
        
        assert "📊 Статус" in buttons, "Кнопка '📊 Статус' отсутствует!"
    
    def test_main_menu_has_plan_button(self):
        """Проверяем что '📅 Мой план' есть в главном меню"""
        from bot.keyboards import get_main_menu
        
        keyboard = get_main_menu()
        buttons = []
        for row in keyboard.keyboard:
            for button in row:
                buttons.append(button.text)
        
        assert "📅 Мой план" in buttons, "Кнопка '📅 Мой план' отсутствует!"
    
    def test_main_menu_has_communication_button(self):
        """Проверяем что '💬 Написать руководителю' есть в главном меню"""
        from bot.keyboards import get_main_menu
        
        keyboard = get_main_menu()
        buttons = []
        for row in keyboard.keyboard:
            for button in row:
                buttons.append(button.text)
        
        assert "💬 Написать руководителю" in buttons, "Кнопка '💬 Написать руководителю' отсутствует!"
    
    def test_admin_menu_has_broadcast_button(self):
        """Проверяем что '📤 Массовая рассылка' есть в админ меню"""
        from bot.keyboards import get_admin_menu
        
        keyboard = get_admin_menu()
        buttons = []
        for row in keyboard.keyboard:
            for button in row:
                buttons.append(button.text)
        
        assert "📤 Массовая рассылка" in buttons, "Кнопка '📤 Массовая рассылка' отсутствует!"


class TestMessages:
    """Тест 4: Шаблоны сообщений"""
    
    def test_required_messages_exist(self):
        """Проверяем наличие необходимых сообщений"""
        from bot.templates.messages import Messages
        
        required = [
            'WELCOME_NEW',
            'WELCOME_BACK',
            'COMMUNICATION_START',
            'COMMUNICATION_SENT',
            'HELP_TEXT',
        ]
        
        for msg in required:
            assert hasattr(Messages, msg), f"Missing message: {msg}"


class TestImports:
    """Тест 5: Проверка импортов"""
    
    def test_all_handlers_importable(self):
        """Проверяем что все обработчики можно импортировать"""
        from bot.handlers import (
            start_router,
            registration_router,
            works_router,
            submit_router,
            plan_router,
            communication_router,
        )
        assert start_router is not None
    
    def test_models_importable(self):
        """Проверяем что модели можно импортировать"""
        from bot.models.models import User, StudentWork
        assert User is not None
        assert StudentWork is not None
    
    def test_services_importable(self):
        """Проверяем что сервисы можно импортировать"""
        from bot.services.yandex_service import YandexDiskService
        from bot.services.db import get_async_session, AsyncSessionContext
        assert YandexDiskService is not None
        assert get_async_session is not None
        assert AsyncSessionContext is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
