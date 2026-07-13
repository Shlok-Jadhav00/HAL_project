AEIA - AI-Powered Engineering Insight Assistant
===============================================
Version: 0.1.0

This package contains the complete, standalone offline analysis application.
No installation of Python, databases, or cloud services is required.

HOW TO INSTALL & RUN:
1. Copy the "AEIA.exe" file from this folder to a permanent location on your PC
   (for example: C:\AEIA\AEIA.exe or your Desktop).
2. Double-click "AEIA.exe" to launch the application.

FIRST RUN:
When you launch the application for the first time, it will take a few seconds
to extract its internal dependencies. It will automatically create a data folder
at:
    C:\Users\<YourUsername>\AppData\Roaming\AEIA

This data folder securely holds your database, settings, rules, and logs.
If you need to back up your historical analysis sessions, simply copy that folder.

TROUBLESHOOTING:
- "Windows protected your PC": If Windows SmartScreen blocks the app, click "More info" and then "Run anyway".
- Antivirus: Some strict antivirus policies may flag the executable due to its bundled nature. Please whitelist AEIA.exe.
- Errors: If the application fails to open or crashes, look for an error log at:
    %APPDATA%\AEIA\logs\aeia_session.log
