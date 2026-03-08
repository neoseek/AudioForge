# LiveprogIDE
Basic embeddable Liveprog IDE, currently supports EELang2 (JamesDSP for Linux)

Designed to be used as a plugin in a QMake subdirs project.

A standalone dummy app can also be compiled by defining the COMPILE_STANDALONE QMake variable.
Example:
```bash
qmake EELEditor.pro "CONFIG += COMPILE_STANDALONE"
```
![Screenshot](screenshot.png)
