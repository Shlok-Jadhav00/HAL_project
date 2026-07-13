"""
AEIA — Color Palette (Core Constants)

Defines raw hex color constants used across the application.
No UI imports (PyQt or ReportLab) are permitted here.
"""

INSTRUMENT_NAVY = '#10243E'
SIGNAL_BLUE = '#2563EB'
ALERT_RED = '#DC2626'
CAUTION_AMBER = '#D97706'
INFO_BLUE = '#1D4ED8'
GRAPHITE = '#111827'
STEEL_LINE = '#D3D8E0'
CONSOLE_GREY = '#F7F8FA'
PANEL_WHITE = '#FFFFFF'
CONFIRMED_GREEN = '#16A34A'
MUTED_SLATE = '#64748B'
INFO_BLUE_BG = '#EFF6FF'
INFO_BLUE_TEXT = '#1E40AF'

# Module specific (from color_philosophy.md)
MODULE_COLORS = {
    'import_validator': '#4F46E5',
    'statistics_engine': '#0EA5E9',
    'anomaly_detector': '#EAB308',
    'expert_system': '#10B981',
    'insight_generator': '#8B5CF6',
    'recommendation_engine': '#F43F5E',
}

MODULE_COLORS = {
    'Import': SIGNAL_BLUE,
    'Anomaly': '#4338CA',
    'Report': '#0EA5E9',
    'History': '#64748B',
    'Settings': '#10B981',
}
