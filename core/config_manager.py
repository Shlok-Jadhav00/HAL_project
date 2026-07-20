import json
import logging
import os
import sys
from typing import Any, Dict

logger = logging.getLogger('aeia.config_manager')

_cached_settings: Dict[str, Any] = {}
_is_loaded: bool = False


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller.
    
    If running as a PyInstaller bundle, sys._MEIPASS is the temporary
    folder where assets are extracted.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def get_app_data_dir() -> str:
    """Get the %APPDATA%/AEIA directory where mutable files live."""
    appdata = os.environ.get('APPDATA', '')
    if not appdata:
        # Fallback for systems without APPDATA
        appdata = os.path.expanduser('~')
    return os.path.join(appdata, 'AEIA')


def get_settings_path() -> str:
    """Return the absolute path to settings.json in AppData."""
    return os.path.join(get_app_data_dir(), 'config', 'settings.json')


def load_settings(force_reload: bool = False) -> Dict[str, Any]:
    """Load and return the settings dictionary from AppData."""
    global _cached_settings, _is_loaded
    
    if _is_loaded and not force_reload:
        return _cached_settings

    settings_path = get_settings_path()
    try:
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                _cached_settings = json.load(f)
            _is_loaded = True
        else:
            logger.warning("settings.json not found at %s. Using empty defaults.", settings_path)
            _cached_settings = {}
            _is_loaded = True
    except Exception as exc:
        logger.error("Failed to load settings.json: %s", exc)
        _cached_settings = {}
    
    return _cached_settings


def resolve_path(path_str: str) -> str:
    """Resolve a path string by expanding environment variables."""
    if not path_str:
        return ""
    expanded = os.path.expandvars(path_str)
    return os.path.normpath(expanded)


def get_rules_path() -> str:
    """Return the absolute path to engineering_rules.json in AppData."""
    settings = load_settings()
    configured_path = settings.get('paths', {}).get('rule_file_path', '')
    
    if configured_path:
        return resolve_path(configured_path)
    
    return os.path.join(get_app_data_dir(), 'rules', 'engineering_rules.json')


def get_database_path() -> str:
    """Return the absolute path to the SQLite database in AppData."""
    settings = load_settings()
    configured_path = settings.get('paths', {}).get('database_path', '')
    
    if configured_path:
        return resolve_path(configured_path)
        
    return os.path.join(get_app_data_dir(), 'database', 'aeia.db')


def get_reports_path() -> str:
    """Return the absolute path to the reports folder."""
    settings = load_settings()
    configured_path = settings.get('paths', {}).get('default_report_folder', '')
    
    if configured_path:
        return resolve_path(configured_path)
    
    # Default to User's Documents folder instead of AppData
    documents_folder = os.path.join(os.path.expanduser('~'), 'Documents', 'AEIA_Reports')
    return documents_folder


def get_logs_path() -> str:
    """Return the absolute path to the logs folder."""
    return os.path.join(get_app_data_dir(), 'logs')

