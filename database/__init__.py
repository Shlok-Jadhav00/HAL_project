# AEIA — Database Access Package
#
# This package manages the SQLite database (aeia.db). It is the ONLY place
# where raw SQL is executed — GUI panels and core modules never run SQL
# directly (code_hygiene_guide.md §1, technical_design.md Part B).
#
# No PyQt5 imports are allowed in this package.
