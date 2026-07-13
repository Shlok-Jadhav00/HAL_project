# AEIA — GUI Presentation Layer Package
#
# This package contains all PyQt5 widgets and panels. It is the ONLY place
# where PyQt5 widgets are created. GUI panels call into core/ and
# database/db_manager.py — they never run raw SQL themselves
# (code_hygiene_guide.md §1, technical_design.md Part B).
