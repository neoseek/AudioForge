#include "FontUtils.h"

#include <QFontDatabase>

QFont FontUtils::preferredMonospaceFont()
{
    bool loadFallbackFont = false;
    int fontRet;
    int fontRet2;
    fontRet = QFontDatabase::addApplicationFont(":/fonts/CONSOLA.ttf");
    fontRet2 = QFontDatabase::addApplicationFont(":/fonts/CONSOLAB.ttf");
    if(fontRet < 0 && fontRet2 < 0)
    {
        loadFallbackFont = true;
    }

    QFont font;
    if(loadFallbackFont){
        font.setFamily("Hack");
    }
    else{
        font.setFamily("Consolas");
    }
    font.setStyleHint(QFont::Monospace);
    font.setPointSize(10);

    return font;
}
