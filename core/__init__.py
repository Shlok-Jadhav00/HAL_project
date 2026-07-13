# AEIA — AI-Powered Engineering Insight Assistant
# Core Analysis Engines Package
#
# This package contains all pure-Python analysis engines. It has ZERO PyQt5
# imports — every module here can be unit-tested headlessly without launching
# the GUI (code_hygiene_guide.md §1, technical_design.md Part B).
#
# The version constant below is the single source of truth for the application
# version. Every other place that needs it (report header FR-072, About panel
# FR-089, PyInstaller .spec file) imports this — it is never hard-coded a
# second time anywhere else (implementation_specification.md §1).

__version__ = "0.1.0"
