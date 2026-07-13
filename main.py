import sys
import os
import logging
import shutil
import traceback
from pathlib import Path

from core.config_manager import (
    get_app_data_dir,
    resource_path,
    get_settings_path,
    get_rules_path,
    get_database_path,
    get_logs_path,
    get_reports_path
)

def initialize_app_data():
    """Create the application data directory and copy default files on first run.

    Directory layout created at %APPDATA%/AEIA/:
        config/settings.json         (from bundled defaults)
        rules/engineering_rules.json (from bundled defaults)
        database/                    (aeia.db created by db_manager)
        reports/                     (empty, for exported PDFs)
        logs/                        (aeia_error.log)
    """
    app_dir = Path(get_app_data_dir())

    for subdir in ['config', 'rules', 'database', 'reports', 'logs']:
        (app_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Copy default config if not already present
    config_dest = Path(get_settings_path())
    if not config_dest.exists():
        config_src = Path(resource_path('config/settings.json'))
        if config_src.exists():
            shutil.copy2(config_src, config_dest)

    # Copy default rules if not already present
    rules_dest = Path(get_rules_path())
    if not rules_dest.exists():
        rules_src = Path(resource_path('rules/engineering_rules.json'))
        if rules_src.exists():
            shutil.copy2(rules_src, rules_dest)


def setup_logging():
    """Configure logging to file and console."""
    app_dir = Path(get_logs_path())
    app_dir.mkdir(parents=True, exist_ok=True)
    log_file = app_dir / 'aeia_session.log'

    handlers = [
        logging.FileHandler(str(log_file), encoding='utf-8'),
    ]
    if not getattr(sys, 'frozen', False):
        handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
    )


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Trap unhandled GUI exceptions and write them to the log file."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger('aeia.unhandled')
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    # Show a message box to the user if QApplication exists
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Critical Error")
            msg.setText("An unexpected error occurred.")
            
            # Format the exception message safely
            err_msg = "".join(traceback.format_exception_only(exc_type, exc_value))
            msg.setInformativeText(str(err_msg))
            msg.setDetailedText("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            msg.exec_()
    except Exception:
        pass


def main():
    """Launch the AEIA desktop application."""
    sys.excepthook = global_exception_handler

    setup_logging()
    logger = logging.getLogger('aeia.main')
    logger.info('AEIA starting up...')

    try:
        initialize_app_data()
        logger.info('Application data directory ready: %s', get_app_data_dir())
    except OSError as exc:
        logger.error('Failed to initialize app data directory: %s', exc)

    from PyQt5.QtWidgets import QApplication
    from gui.main_window import MainWindow
    from core import __version__

    app = QApplication(sys.argv)
    app.setApplicationName('AEIA')
    app.setApplicationVersion(__version__)

    from database.db_manager import DatabaseManager
    db_path = get_database_path()
    db_manager = DatabaseManager(str(db_path))
    db_manager.initialize_schema()
    logger.info('Database initialized at: %s', db_path)

    window = MainWindow(db_manager)
    window.show()
    logger.info('Main window displayed — AEIA v%s ready.', __version__)

    exit_code = app.exec_()
    logger.info('AEIA shutting down (exit code %d).', exit_code)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

