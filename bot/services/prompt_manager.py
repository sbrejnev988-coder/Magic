"""
РњРµРЅРµРґР¶РµСЂ РїСЂРѕРјРїС‚РѕРІ РґР»СЏ MysticBot.
Р—Р°РіСЂСѓР¶Р°РµС‚ СЃРїРµС†РёР°Р»РёР·РёСЂРѕРІР°РЅРЅС‹Рµ РїСЂРѕРјРїС‚С‹ РґР»СЏ 11 РјРѕРґСѓР»РµР№, РїРѕРґРґРµСЂР¶РёРІР°РµС‚ РїРµСЂСЃРѕРЅР°Р»РёР·Р°С†РёСЋ РґР°РЅРЅС‹С… РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape

from bot.models.user_profile import UserProfile
from bot.config import Settings

log = logging.getLogger(__name__)


class PromptManager:
    """РЈРїСЂР°РІР»РµРЅРёРµ РїСЂРѕРјРїС‚Р°РјРё СЃ РїРµСЂСЃРѕРЅР°Р»РёР·Р°С†РёРµР№."""

    # РЎРѕРѕС‚РІРµС‚СЃС‚РІРёРµ РјРµР¶РґСѓ РЅР°Р·РІР°РЅРёСЏРјРё РјРѕРґСѓР»РµР№ Рё РёРјРµРЅР°РјРё С„Р°Р№Р»РѕРІ РїСЂРѕРјРїС‚РѕРІ
    MODULE_PROMPT_MAP = {
        "tarot": "tarot.md",
        "numerology": "numerology.md",
        "astrology": "astrology.md",
        "aura": "aura.md",
        "dream": "dream.md",
        "meditation": "meditation.md",
        "runes": "runes.md",
        "iching": "iching.md",
        "horoscope_daily": "horoscope_daily.md",
        "compatibility": "compatibility.md",
        "affirmation": "affirmation.md",
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self._prompt_cache: Dict[str, str] = {}
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            autoescape=select_autoescape(['md', 'txt']),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def get_prompt_for_module(self, module_name: str, user_profile: Optional[UserProfile] = None, **kwargs) -> str:
        """
        Р’РѕР·РІСЂР°С‰Р°РµС‚ РїСЂРѕРјРїС‚ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ РјРѕРґСѓР»СЏ СЃ РїРµСЂСЃРѕРЅР°Р»РёР·Р°С†РёРµР№.
        
        Args:
            module_name: РЅР°Р·РІР°РЅРёРµ РјРѕРґСѓР»СЏ (tarot, numerology, ...)
            user_profile: РїСЂРѕС„РёР»СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РґР»СЏ РїРµСЂСЃРѕРЅР°Р»РёР·Р°С†РёРё
            **kwargs: РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ РґР»СЏ РїРѕРґСЃС‚Р°РЅРѕРІРєРё
        
        Returns:
            Р“РѕС‚РѕРІС‹Р№ РїСЂРѕРјРїС‚ СЃ РїРѕРґСЃС‚Р°РІР»РµРЅРЅС‹РјРё Р·РЅР°С‡РµРЅРёСЏРјРё
        """
        if module_name not in self.MODULE_PROMPT_MAP:
            log.warning(f"РњРѕРґСѓР»СЊ '{module_name}' РЅРµ РЅР°Р№РґРµРЅ РІ РєР°СЂС‚Рµ РїСЂРѕРјРїС‚РѕРІ. РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РѕР±С‰РёР№ РїСЂРѕРјРїС‚.")
            return self._get_fallback_prompt(module_name, user_profile, **kwargs)
        
        prompt_file = self.MODULE_PROMPT_MAP[module_name]
        try:
            template = self._jinja_env.get_template(prompt_file)
        except Exception as e:
            log.error(f"РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ С€Р°Р±Р»РѕРЅ РїСЂРѕРјРїС‚Р° '{prompt_file}': {e}")
            return self._get_fallback_prompt(module_name, user_profile, **kwargs)
        
        context = self._build_context(user_profile, **kwargs)
        return template.render(**context)

    def _build_context(self, user_profile: Optional[UserProfile] = None, **extra) -> Dict[str, Any]:
        """РЎС‚СЂРѕРёС‚ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ РїРѕРґСЃС‚Р°РЅРѕРІРєРё РІ РїСЂРѕРјРїС‚."""
        context = {}
        
        if user_profile:
            context.update(user_profile.to_prompt_context())
            # Р”РѕР±Р°РІР»СЏРµРј СЂСѓСЃСЃРєРёРµ РЅР°Р·РІР°РЅРёСЏ РґР»СЏ СѓРґРѕР±СЃС‚РІР°
            context["user_name_ru"] = user_profile.full_name
            context["zodiac_sign_ru"] = self._translate_zodiac(user_profile.zodiac_sign) if user_profile.zodiac_sign else "РЅРµРёР·РІРµСЃС‚РµРЅ"
            context["zodiac_element_ru"] = self._translate_element(user_profile.zodiac_element) if user_profile.zodiac_element else "РЅРµРёР·РІРµСЃС‚РЅР°"
        
        # Р—РЅР°С‡РµРЅРёСЏ РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
        context.setdefault("user_name", "РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ")
        context.setdefault("first_name", "РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ")
        context.setdefault("zodiac_sign", "РЅРµРёР·РІРµСЃС‚РµРЅ")
        context.setdefault("zodiac_element", "РЅРµРёР·РІРµСЃС‚РЅР°")
        context.setdefault("age", "РЅРµ СѓРєР°Р·Р°РЅ")
        context.setdefault("ruling_planet", "РЅРµ СѓРєР°Р·Р°РЅ")
        context.setdefault("preferred_module", "РЅРµ СѓРєР°Р·Р°РЅ")
        
        # Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ
        context.update(extra)
        return context

    def _get_fallback_prompt(self, module_name: str, user_profile: Optional[UserProfile], **kwargs) -> str:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ Р·Р°РїР°СЃРЅРѕР№ РїСЂРѕРјРїС‚, РµСЃР»Рё СЃРїРµС†РёР°Р»РёР·РёСЂРѕРІР°РЅРЅС‹Р№ РЅРµ РЅР°Р№РґРµРЅ."""
        context = self._build_context(user_profile, **kwargs)
        
        fallback = f"""Р’С‹ вЂ” СЌРєСЃРїРµСЂС‚ РІ РѕР±Р»Р°СЃС‚Рё {module_name}. 
РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ {{user_name}} (Р·РЅР°Рє Р·РѕРґРёР°РєР°: {{zodiac_sign}}, СЃС‚РёС…РёСЏ: {{zodiac_element}}) РѕР±СЂР°С‚РёР»СЃСЏ Рє РІР°Рј Р·Р° РєРѕРЅСЃСѓР»СЊС‚Р°С†РёРµР№.
РџСЂРѕР°РЅР°Р»РёР·РёСЂСѓР№С‚Рµ Р·Р°РїСЂРѕСЃ Рё РґР°Р№С‚Рµ РґРµС‚Р°Р»СЊРЅС‹Р№, РїРµСЂСЃРѕРЅР°Р»РёР·РёСЂРѕРІР°РЅРЅС‹Р№ РѕС‚РІРµС‚, СѓС‡РёС‚С‹РІР°СЏ РѕСЃРѕР±РµРЅРЅРѕСЃС‚Рё Р·РЅР°РєР° Рё С…Р°СЂР°РєС‚РµСЂР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.

Р—Р°РїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ: {{query}}

РЎС„РѕСЂРјСѓР»РёСЂСѓР№С‚Рµ РѕС‚РІРµС‚ РІ С„РѕСЂРјР°С‚Рµ, СЃРѕРѕС‚РІРµС‚СЃС‚РІСѓСЋС‰РµРј С‚РµРјРµ {module_name}."""
        
        template = Template(fallback)
        return template.render(**context)

    @staticmethod
    def _translate_zodiac(zodiac_enum) -> str:
        """РџРµСЂРµРІРѕРґРёС‚ Р·РЅР°Рє Р·РѕРґРёР°РєР° РЅР° СЂСѓСЃСЃРєРёР№."""
        mapping = {
            "aries": "РћРІРµРЅ",
            "taurus": "РўРµР»РµС†",
            "gemini": "Р‘Р»РёР·РЅРµС†С‹",
            "cancer": "Р Р°Рє",
            "leo": "Р›РµРІ",
            "virgo": "Р”РµРІР°",
            "libra": "Р’РµСЃС‹",
            "scorpio": "РЎРєРѕСЂРїРёРѕРЅ",
            "sagittarius": "РЎС‚СЂРµР»РµС†",
            "capricorn": "РљРѕР·РµСЂРѕРі",
            "aquarius": "Р’РѕРґРѕР»РµР№",
            "pisces": "Р С‹Р±С‹"
        }
        return mapping.get(zodiac_enum.value, zodiac_enum.value)

    @staticmethod
    def _translate_element(element: str) -> str:
        """РџРµСЂРµРІРѕРґРёС‚ СЃС‚РёС…РёСЋ РЅР° СЂСѓСЃСЃРєРёР№."""
        mapping = {
            "fire": "РѕРіРѕРЅСЊ",
            "earth": "Р·РµРјР»СЏ",
            "air": "РІРѕР·РґСѓС…",
            "water": "РІРѕРґР°"
        }
        return mapping.get(element.lower(), element)

    def list_available_modules(self) -> list:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РјРѕРґСѓР»РµР№."""
        return list(self.MODULE_PROMPT_MAP.keys())

    def module_exists(self, module_name: str) -> bool:
        """РџСЂРѕРІРµСЂСЏРµС‚, СЃСѓС‰РµСЃС‚РІСѓРµС‚ Р»Рё РїСЂРѕРјРїС‚ РґР»СЏ РјРѕРґСѓР»СЏ."""
        if module_name not in self.MODULE_PROMPT_MAP:
            return False
        prompt_file = self.prompts_dir / self.MODULE_PROMPT_MAP[module_name]
        return prompt_file.exists()