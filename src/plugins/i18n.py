"""
Ableton Brain - Phase 4: Internationalization (i18n)
Multi-language support for UI, API messages, and documentation
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


class SupportedLocale(Enum):
    """Supported locales"""
    EN_US = "en-US"   # English (US)
    EN_GB = "en-GB"   # English (UK)
    ES_ES = "es-ES"   # Spanish (Spain)
    ES_MX = "es-MX"   # Spanish (Mexico)
    FR_FR = "fr-FR"   # French (France)
    DE_DE = "de-DE"   # German (Germany)
    JA_JP = "ja-JP"   # Japanese
    KO_KR = "ko-KR"   # Korean
    ZH_CN = "zh-CN"   # Chinese (Simplified)
    ZH_TW = "zh-TW"   # Chinese (Traditional)
    PT_BR = "pt-BR"   # Portuguese (Brazil)
    IT_IT = "it-IT"   # Italian
    RU_RU = "ru-RU"   # Russian
    NL_NL = "nl-NL"   # Dutch
    PL_PL = "pl-PL"   # Polish


@dataclass
class LocaleInfo:
    """Locale metadata"""
    code: str
    name: str
    native_name: str
    rtl: bool = False
    plural_rules: str = "nplurals=2; plural=(n != 1);"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "HH:mm"
    number_format: str = "1,234.56"
    currency: str = "USD"
    region: str = ""


# Locale metadata
LOCALE_INFO = {
    SupportedLocale.EN_US: LocaleInfo("en-US", "English (US)", "English (US)", currency="USD", region="US"),
    SupportedLocale.EN_GB: LocaleInfo("en-GB", "English (UK)", "English (UK)", currency="GBP", region="GB"),
    SupportedLocale.ES_ES: LocaleInfo("es-ES", "Spanish (Spain)", "Español (España)", currency="EUR", region="ES"),
    SupportedLocale.ES_MX: LocaleInfo("es-MX", "Spanish (Mexico)", "Español (México)", currency="MXN", region="MX"),
    SupportedLocale.FR_FR: LocaleInfo("fr-FR", "French (France)", "Français (France)", currency="EUR", region="FR"),
    SupportedLocale.DE_DE: LocaleInfo("de-DE", "German (Germany)", "Deutsch (Deutschland)", currency="EUR", region="DE"),
    SupportedLocale.JA_JP: LocaleInfo("ja-JP", "Japanese", "日本語", date_format="YYYY/MM/DD", currency="JPY", region="JP"),
    SupportedLocale.KO_KR: LocaleInfo("ko-KR", "Korean", "한국어", date_format="YYYY.MM.DD", currency="KRW", region="KR"),
    SupportedLocale.ZH_CN: LocaleInfo("zh-CN", "Chinese (Simplified)", "中文 (简体)", date_format="YYYY年MM月DD日", currency="CNY", region="CN"),
    SupportedLocale.ZH_TW: LocaleInfo("zh-TW", "Chinese (Traditional)", "中文 (繁體)", date_format="YYYY年MM月DD日", currency="TWD", region="TW"),
    SupportedLocale.PT_BR: LocaleInfo("pt-BR", "Portuguese (Brazil)", "Português (Brasil)", currency="BRL", region="BR"),
    SupportedLocale.IT_IT: LocaleInfo("it-IT", "Italian (Italy)", "Italiano (Italia)", currency="EUR", region="IT"),
    SupportedLocale.RU_RU: LocaleInfo("ru-RU", "Russian", "Русский", currency="RUB", region="RU"),
    SupportedLocale.NL_NL: LocaleInfo("nl-NL", "Dutch", "Nederlands", currency="EUR", region="NL"),
    SupportedLocale.PL_PL: LocaleInfo("pl-PL", "Polish", "Polski", plural_rules="nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);", currency="PLN", region="PL"),
}


@dataclass
class TranslationEntry:
    """Single translation entry"""
    key: str
    locale: str
    value: str
    context: Optional[str] = None
    plural_forms: Dict[str, str] = field(default_factory=dict)  # For pluralization
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    verified: bool = False


class I18nManager:
    """Internationalization manager"""
    
    def __init__(self, locales_dir: Path, default_locale: str = "en-US"):
        self.locales_dir = Path(locales_dir)
        self.locales_dir.mkdir(parents=True, exist_ok=True)
        self.default_locale = default_locale
        self.current_locale = default_locale
        
        self._translations: Dict[str, Dict[str, TranslationEntry]] = defaultdict(dict)  # locale -> key -> entry
        self._fallback_chain: Dict[str, List[str]] = {}  # locale -> fallback locales
        
        self._load_all()
        self._build_fallback_chains()
    
    def _load_all(self):
        """Load all translation files"""
        for locale in SupportedLocale:
            locale_file = self.locales_dir / f"{locale.value}.json"
            if locale_file.exists():
                self._load_locale(locale.value, locale_file)
    
    def _load_locale(self, locale: str, filepath: Path):
        """Load translations for a locale"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for key, entry_data in data.items():
                if isinstance(entry_data, str):
                    # Simple string format
                    self._translations[locale][key] = TranslationEntry(
                        key=key, locale=locale, value=entry_data
                    )
                elif isinstance(entry_data, dict):
                    # Full entry format
                    self._translations[locale][key] = TranslationEntry(**entry_data)
        except Exception as e:
            print(f"Failed to load locale {locale}: {e}")
    
    def _build_fallback_chains(self):
        """Build fallback chains for each locale"""
        for locale in SupportedLocale:
            chain = [locale.value]
            # Add base language fallback (e.g., es-ES -> es)
            if '-' in locale.value:
                base = locale.value.split('-')[0]
                # Find matching locale
                for l in SupportedLocale:
                    if l.value.startswith(base + '-') and l.value != locale.value:
                        chain.append(l.value)
                        break
            # Add default locale as final fallback
            if self.default_locale not in chain:
                chain.append(self.default_locale)
            self._fallback_chain[locale.value] = chain
    
    def set_locale(self, locale: str) -> bool:
        """Set current locale"""
        if locale in [l.value for l in SupportedLocale]:
            self.current_locale = locale
            return True
        return False
    
    def get_locale(self) -> str:
        return self.current_locale
    
    def t(self, key: str, locale: str = None, **kwargs) -> str:
        """Translate a key"""
        locale = locale or self.current_locale
        
        # Try current locale
        entry = self._translations.get(locale, {}).get(key)
        if entry:
            return self._format_value(entry.value, kwargs)
        
        # Try fallback chain
        for fallback_locale in self._fallback_chain.get(locale, [self.default_locale]):
            entry = self._translations.get(fallback_locale, {}).get(key)
            if entry:
                return self._format_value(entry.value, kwargs)
        
        # Return key as fallback
        return key
    
    def _format_value(self, value: str, kwargs: Dict) -> str:
        """Format translation with variables"""
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    def t_plural(self, key: str, count: int, locale: str = None, **kwargs) -> str:
        """Translate with pluralization"""
        locale = locale or self.current_locale
        kwargs['count'] = count
        
        entry = self._translations.get(locale, {}).get(key)
        if not entry:
            # Fallback
            for fallback_locale in self._fallback_chain.get(locale, [self.default_locale]):
                entry = self._translations.get(fallback_locale, {}).get(key)
                if entry:
                    break
        
        if not entry:
            return key
        
        # Determine plural form
        plural_form = self._get_plural_form(count, locale)
        
        # Use plural form if available
        if plural_form in entry.plural_forms:
            return self._format_value(entry.plural_forms[plural_form], kwargs)
        
        return self._format_value(entry.value, kwargs)
    
    def _get_plural_form(self, count: int, locale: str) -> str:
        """Get plural form for count and locale"""
        # Simplified plural rules
        if locale.startswith('en'):
            return 'one' if count == 1 else 'other'
        elif locale.startswith('fr') or locale.startswith('pt') or locale.startswith('es'):
            return 'one' if count == 0 or count == 1 else 'other'
        elif locale.startswith('de') or locale.startswith('nl') or locale.startswith('it'):
            return 'one' if count == 1 else 'other'
        elif locale.startswith('pl'):
            if count == 1:
                return 'one'
            elif count % 10 >= 2 and count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                return 'few'
            else:
                return 'many'
        elif locale.startswith('ru'):
            if count % 10 == 1 and count % 100 != 11:
                return 'one'
            elif count % 10 in [2, 3, 4] and count % 100 not in [12, 13, 14]:
                return 'few'
            else:
                return 'many'
        elif locale.startswith('ja') or locale.startswith('ko') or locale.startswith('zh'):
            return 'other'  # No plural distinction
        else:
            return 'other'
    
    def add_translation(self, key: str, locale: str, value: str, 
                        context: str = None, plural_forms: Dict = None) -> TranslationEntry:
        """Add or update a translation"""
        entry = TranslationEntry(
            key=key,
            locale=locale,
            value=value,
            context=context,
            plural_forms=plural_forms or {}
        )
        self._translations[locale][key] = entry
        return entry
    
    def save_locale(self, locale: str):
        """Save locale to file"""
        filepath = self.locales_dir / f"{locale}.json"
        data = {}
        for key, entry in self._translations.get(locale, {}).items():
            if entry.plural_forms:
                data[key] = asdict(entry)
            else:
                data[key] = entry.value
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_missing_keys(self, locale: str) -> List[str]:
        """Get keys missing in locale compared to default"""
        default_keys = set(self._translations.get(self.default_locale, {}).keys())
        locale_keys = set(self._translations.get(locale, {}).keys())
        return sorted(default_keys - locale_keys)
    
    def get_completion_stats(self) -> Dict[str, Dict]:
        """Get translation completion stats"""
        default_keys = set(self._translations.get(self.default_locale, {}).keys())
        total = len(default_keys)
        
        stats = {}
        for locale in [l.value for l in SupportedLocale]:
            locale_keys = set(self._translations.get(locale, {}).keys())
            translated = len(default_keys & locale_keys)
            stats[locale] = {
                "total": total,
                "translated": translated,
                "missing": total - translated,
                "percentage": (translated / total * 100) if total > 0 else 0
            }
        return stats
    
    def export_locale(self, locale: str, format: str = "json") -> str:
        """Export locale in various formats"""
        entries = self._translations.get(locale, {})
        
        if format == "json":
            data = {k: v.value for k, v in entries.items()}
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format == "po":
            # Gettext PO format
            lines = [
                f'msgid ""',
                f'msgstr ""',
                f'"Project-Id-Version: Ableton Brain\\n"',
                f'"Language: {locale}\\n"',
                f'"Content-Type: text/plain; charset=UTF-8\\n"',
                ""
            ]
            for key, entry in entries.items():
                lines.append(f'#. {entry.context or ""}')
                lines.append(f'msgid "{key}"')
                lines.append(f'msgstr "{entry.value}"')
                lines.append("")
            return "\n".join(lines)
        elif format == "csv":
            # CSV format
            lines = ["key,value,context"]
            for key, entry in entries.items():
                context = (entry.context or "").replace('"', '""')
                value = entry.value.replace('"', '""')
                lines.append(f'"{key}","{value}","{context}"')
            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


# Built-in translations for core UI strings
CORE_TRANSLATIONS = {
    "en-US": {
        # General
        "app.name": "Ableton Brain",
        "app.tagline": "Cross-DAW Music Production Automation",
        "app.version": "Version {version}",
        
        # Navigation
        "nav.dashboard": "Dashboard",
        "nav.tracks": "Tracks",
        "nav.transport": "Transport",
        "nav.controllers": "Controllers",
        "nav.daws": "DAWs",
        "nav.quick": "Quick Actions",
        "nav.collab": "Collaboration",
        "nav.projects": "Projects",
        "nav.templates": "Templates",
        "nav.learning": "Learning",
        "nav.settings": "Settings",
        
        # Dashboard
        "dashboard.title": "Dashboard",
        "dashboard.active_daw": "Active DAW",
        "dashboard.connected": "Connected",
        "dashboard.disconnected": "Disconnected",
        "dashboard.controllers": "Controllers",
        "dashboard.tempo": "Tempo",
        "dashboard.time_signature": "Time Signature",
        "dashboard.sample_rate": "Sample Rate",
        
        # Tracks
        "tracks.title": "Tracks",
        "tracks.create": "Create Track",
        "tracks.name": "Name",
        "tracks.type": "Type",
        "tracks.midi": "MIDI",
        "tracks.audio": "Audio",
        "tracks.return": "Return",
        "tracks.master": "Master",
        "tracks.volume": "Volume",
        "tracks.pan": "Pan",
        "tracks.mute": "Mute",
        "tracks.solo": "Solo",
        "tracks.arm": "Arm",
        "tracks.delete": "Delete",
        "tracks.no_tracks": "No tracks in project",
        
        # Transport
        "transport.title": "Transport",
        "transport.play": "Play",
        "transport.stop": "Stop",
        "transport.record": "Record",
        "transport.loop": "Loop",
        "transport.metronome": "Metronome",
        "transport.tempo": "Tempo",
        "transport.time_signature": "Time Signature",
        "transport.position": "Position",
        
        # Controllers
        "controllers.title": "Controllers",
        "controllers.detect": "Detect Controllers",
        "controllers.connect": "Connect",
        "controllers.disconnect": "Disconnect",
        "controllers.map": "Map",
        "controllers.no_controllers": "No controllers detected",
        "controllers.midi_input": "MIDI Input",
        "controllers.midi_output": "MIDI Output",
        
        # DAWs
        "daws.title": "DAWs",
        "daws.connect": "Connect",
        "daws.disconnect": "Disconnect",
        "daws.available": "Available DAWs",
        "daws.active": "Active DAW",
        
        # Collaboration
        "collab.title": "Collaboration",
        "collab.join_session": "Join Session",
        "collab.create_session": "Create Session",
        "collab.leave_session": "Leave Session",
        "collab.room_id": "Room ID",
        "collab.peer_name": "Your Name",
        "collab.peers": "Peers",
        "collab.chat": "Chat",
        "collab.send": "Send",
        "collab.cursor": "Cursor",
        "collab.selection": "Selection",
        
        # Projects
        "projects.title": "Projects",
        "projects.share": "Share Project",
        "projects.export": "Export",
        "projects.import": "Import",
        "projects.fork": "Fork",
        "projects.visibility": "Visibility",
        "projects.private": "Private",
        "projects.link": "Anyone with Link",
        "projects.public": "Public",
        "projects.tags": "Tags",
        "projects.description": "Description",
        
        # Templates
        "templates.title": "Templates",
        "templates.create": "Create Template",
        "templates.category": "Category",
        "templates.difficulty": "Difficulty",
        "templates.beginner": "Beginner",
        "templates.intermediate": "Intermediate",
        "templates.advanced": "Advanced",
        "templates.estimated_time": "Estimated Time",
        "templates.required_plugins": "Required Plugins",
        
        # Learning
        "learning.title": "Learning Paths",
        "learning.create_path": "Create Learning Path",
        "learning.modules": "Modules",
        "learning.prerequisites": "Prerequisites",
        "learning.estimated_hours": "Estimated Hours",
        
        # Settings
        "settings.title": "Settings",
        "settings.language": "Language",
        "settings.theme": "Theme",
        "settings.notifications": "Notifications",
        "settings.api_key": "API Key",
        "settings.webhooks": "Webhooks",
        "settings.save": "Save",
        
        # Common
        "common.save": "Save",
        "common.cancel": "Cancel",
        "common.delete": "Delete",
        "common.edit": "Edit",
        "common.create": "Create",
        "common.loading": "Loading...",
        "common.error": "Error",
        "common.success": "Success",
        "common.warning": "Warning",
        "common.info": "Info",
        "common.confirm": "Confirm",
        "common.close": "Close",
        "common.search": "Search",
        "common.filter": "Filter",
        "common.sort": "Sort",
        "common.refresh": "Refresh",
        
        # Errors
        "error.connection_failed": "Connection failed",
        "error.daw_not_connected": "No DAW connected",
        "error.project_not_found": "Project not found",
        "error.track_not_found": "Track not found",
        "error.permission_denied": "Permission denied",
        "error.invalid_input": "Invalid input",
        "error.server_error": "Server error",
        
        # Plural forms
        "tracks.count": {
            "value": "{count} tracks",
            "plural_forms": {"one": "1 track", "other": "{count} tracks"}
        },
        "peers.count": {
            "value": "{count} peers",
            "plural_forms": {"one": "1 peer", "other": "{count} peers"}
        },
        "templates.count": {
            "value": "{count} templates",
            "plural_forms": {"one": "1 template", "other": "{count} templates"}
        }
    },
    
    "es-ES": {
        "app.name": "Ableton Brain",
        "app.tagline": "Automatización de Producción Musical Multi-DAW",
        
        "nav.dashboard": "Panel",
        "nav.tracks": "Pistas",
        "nav.transport": "Transporte",
        "nav.controllers": "Controladores",
        "nav.daws": "DAWs",
        "nav.quick": "Acciones Rápidas",
        "nav.collab": "Colaboración",
        "nav.projects": "Proyectos",
        "nav.templates": "Plantillas",
        "nav.learning": "Aprendizaje",
        "nav.settings": "Ajustes",
        
        "dashboard.title": "Panel de Control",
        "dashboard.active_daw": "DAW Activa",
        "dashboard.connected": "Conectado",
        "dashboard.disconnected": "Desconectado",
        
        "tracks.title": "Pistas",
        "tracks.create": "Crear Pista",
        "tracks.midi": "MIDI",
        "tracks.audio": "Audio",
        
        "transport.title": "Transporte",
        "transport.play": "Reproducir",
        "transport.stop": "Detener",
        "transport.record": "Grabar",
        
        "controllers.title": "Controladores",
        "controllers.detect": "Detectar Controladores",
        
        "daws.title": "DAWs",
        "daws.connect": "Conectar",
        
        "collab.title": "Colaboración",
        "collab.join_session": "Unirse a Sesión",
        "collab.peers": "Participantes",
        
        "projects.title": "Proyectos",
        "projects.share": "Compartir",
        
        "common.save": "Guardar",
        "common.cancel": "Cancelar",
        "common.delete": "Eliminar",
        "common.loading": "Cargando...",
        "common.error": "Error",
        "common.success": "Éxito",
        
        "tracks.count": {
            "value": "{count} pistas",
            "plural_forms": {"one": "1 pista", "other": "{count} pistas"}
        }
    },
    
    "fr-FR": {
        "app.name": "Ableton Brain",
        "app.tagline": "Automatisation de Production Musicale Multi-DAW",
        
        "nav.dashboard": "Tableau de bord",
        "nav.tracks": "Pistes",
        "nav.transport": "Transport",
        "nav.controllers": "Contrôleurs",
        
        "dashboard.title": "Tableau de bord",
        "dashboard.connected": "Connecté",
        
        "tracks.title": "Pistes",
        "tracks.create": "Créer une piste",
        
        "transport.title": "Transport",
        "transport.play": "Lecture",
        "transport.stop": "Arrêt",
        
        "common.save": "Enregistrer",
        "common.cancel": "Annuler",
        "common.delete": "Supprimer",
        "common.loading": "Chargement...",
        
        "tracks.count": {
            "value": "{count} pistes",
            "plural_forms": {"one": "1 piste", "other": "{count} pistes"}
        }
    },
    
    "de-DE": {
        "app.name": "Ableton Brain",
        "app.tagline": "Cross-DAW Musikproduktions-Automatisierung",
        
        "nav.dashboard": "Dashboard",
        "nav.tracks": "Spuren",
        "nav.transport": "Transport",
        "nav.controllers": "Controller",
        
        "dashboard.title": "Dashboard",
        "dashboard.connected": "Verbunden",
        
        "tracks.title": "Spuren",
        "tracks.create": "Spur erstellen",
        
        "transport.title": "Transport",
        "transport.play": "Wiedergabe",
        "transport.stop": "Stopp",
        
        "common.save": "Speichern",
        "common.cancel": "Abbrechen",
        "common.delete": "Löschen",
        "common.loading": "Laden...",
        
        "tracks.count": {
            "value": "{count} Spuren",
            "plural_forms": {"one": "1 Spur", "other": "{count} Spuren"}
        }
    },
    
    "ja-JP": {
        "app.name": "Ableton Brain",
        "app.tagline": "クロスDAW音楽制作自動化",
        
        "nav.dashboard": "ダッシュボード",
        "nav.tracks": "トラック",
        "nav.transport": "トランスポート",
        "nav.controllers": "コントローラー",
        
        "dashboard.title": "ダッシュボード",
        "dashboard.connected": "接続済み",
        
        "tracks.title": "トラック",
        "tracks.create": "トラック作成",
        
        "transport.title": "トランスポート",
        "transport.play": "再生",
        "transport.stop": "停止",
        
        "common.save": "保存",
        "common.cancel": "キャンセル",
        "common.delete": "削除",
        "common.loading": "読み込み中...",
        
        "tracks.count": {
            "value": "{count}トラック",
            "plural_forms": {"other": "{count}トラック"}
        }
    },
    
    "zh-CN": {
        "app.name": "Ableton Brain",
        "app.tagline": "跨DAW音乐制作自动化",
        
        "nav.dashboard": "仪表盘",
        "nav.tracks": "轨道",
        "nav.transport": "传输控制",
        "nav.controllers": "控制器",
        
        "dashboard.title": "仪表盘",
        "dashboard.connected": "已连接",
        
        "tracks.title": "轨道",
        "tracks.create": "创建轨道",
        
        "transport.title": "传输控制",
        "transport.play": "播放",
        "transport.stop": "停止",
        
        "common.save": "保存",
        "common.cancel": "取消",
        "common.delete": "删除",
        "common.loading": "加载中...",
        
        "tracks.count": {
            "value": "{count} 条轨道",
            "plural_forms": {"other": "{count} 条轨道"}
        }
    }
}


def create_builtin_translations(locales_dir: Path):
    """Create built-in translation files"""
    locales_dir.mkdir(parents=True, exist_ok=True)
    
    for locale, translations in CORE_TRANSLATIONS.items():
        filepath = locales_dir / f"{locale}.json"
        if not filepath.exists():
            # Convert plural forms to full entry format
            data = {}
            for key, value in translations.items():
                if isinstance(value, dict) and "plural_forms" in value:
                    data[key] = {
                        "key": key,
                        "locale": locale,
                        "value": value["value"],
                        "plural_forms": value["plural_forms"]
                    }
                else:
                    data[key] = value
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Created {locale}.json")


# Language detection
def detect_language(request_headers: Dict = None, accept_language: str = None) -> str:
    """Detect best matching locale from request"""
    if accept_language:
        # Parse Accept-Language header
        # Format: "en-US,en;q=0.9,es;q=0.8"
        langs = []
        for part in accept_language.split(','):
            part = part.strip()
            q = 1.0
            if ';' in part:
                lang_part, q_part = part.split(';', 1)
                lang = lang_part.strip()
                if q_part.strip().startswith('q='):
                    q = float(q_part.split('=')[1])
            else:
                lang = part
            langs.append((lang, q))
        
        # Sort by quality
        langs.sort(key=lambda x: x[1], reverse=True)
        
        # Find best match
        for lang, _ in langs:
            # Normalize
            lang = lang.replace('_', '-')
            for locale in SupportedLocale:
                if locale.value.lower() == lang.lower() or locale.value.split('-')[0].lower() == lang.split('-')[0].lower():
                    return locale.value
    
    return "en-US"


if __name__ == "__main__":
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp:
        locales_dir = Path(tmp) / "locales"
        
        # Create built-in translations
        create_builtin_translations(locales_dir)
        
        # Test i18n manager
        i18n = I18nManager(locales_dir)
        
        # Test translations
        print(f"Default locale: {i18n.get_locale()}")
        print(f"EN: {i18n.t('app.name')}")
        print(f"EN tracks: {i18n.t('tracks.title')}")
        print(f"EN plural: {i18n.t_plural('tracks.count', 1)}")
        print(f"EN plural: {i18n.t_plural('tracks.count', 5)}")
        
        i18n.set_locale("es-ES")
        print(f"ES: {i18n.t('app.name')}")
        print(f"ES tracks: {i18n.t('tracks.title')}")
        print(f"ES plural: {i18n.t_plural('tracks.count', 1)}")
        print(f"ES plural: {i18n.t_plural('tracks.count', 5)}")
        
        i18n.set_locale("ja-JP")
        print(f"JA: {i18n.t('app.name')}")
        print(f"JA plural: {i18n.t_plural('tracks.count', 1)}")
        print(f"JA plural: {i18n.t_plural('tracks.count', 5)}")
        
        # Completion stats
        stats = i18n.get_completion_stats()
        for locale, stat in stats.items():
            if stat["translated"] > 0:
                print(f"{locale}: {stat['translated']}/{stat['total']} ({stat['percentage']:.1f}%)")