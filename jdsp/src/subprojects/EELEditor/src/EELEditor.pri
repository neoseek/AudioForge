!HEADLESS {
    include(../3rdparty/QCodeEditor/QCodeEditor.pri)
    include(../3rdparty/docking-system/src/ads-plugin.pri)

    SOURCES += \
        $$PWD/eeleditor.cpp \
        $$PWD/model/completerdelegate.cpp \
        $$PWD/model/customsymbolprovider.cpp \
        $$PWD/model/eelcompleter.cpp \
        $$PWD/model/eelhighlighter.cpp \
        $$PWD/utils/FontUtils.cpp \
        $$PWD/widgets/ActionButton.cpp \
        $$PWD/widgets/EmptyView.cpp \
        $$PWD/widgets/VariableWatchWidget.cpp \
        $$PWD/widgets/codeeditor.cpp \
        $$PWD/widgets/codeoutline.cpp \
        $$PWD/widgets/consoleoutput.cpp \
        $$PWD/widgets/dialog/newfilewizard.cpp \
        $$PWD/widgets/findreplaceform.cpp \
        $$PWD/widgets/projectview.cpp

    HEADERS += \
        $$PWD/eeleditor.h \
        $$PWD/model/completerdelegate.h \
        $$PWD/model/customsymbolprovider.h \
        $$PWD/model/eelcompleter.h \
        $$PWD/model/eelhighlighter.h \
        $$PWD/utils/FontUtils.h \
        $$PWD/widgets/ActionButton.h \
        $$PWD/widgets/EmptyView.h \
        $$PWD/widgets/VariableWatchWidget.h \
        $$PWD/widgets/codeeditor.h \
        $$PWD/widgets/codeoutline.h \
        $$PWD/widgets/consoleoutput.h \
        $$PWD/widgets/dialog/newfilewizard.h \
        $$PWD/widgets/findreplaceform.h \
        $$PWD/widgets/projectview.h \
        $$PWD/widgets/proxystyle.h

    FORMS += \
        $$PWD/eeleditor.ui \
        $$PWD/widgets/EmptyView.ui \
        $$PWD/widgets/VariableWatchWidget.ui \
        $$PWD/widgets/dialog/newfilewizard.ui \
        $$PWD/widgets/findreplaceform.ui
}

SOURCES += \
    $$PWD/model/VariableItemModel.cpp \
    $$PWD/utils/stringutils.cpp

HEADERS += \
    $$PWD/model/VariableItemModel.h \
    $$PWD/model/abstractdefinition.h \
    $$PWD/utils/stringutils.h \
    $$PWD/model/annotationdefinition.h \
    $$PWD/model/codecontainer.h \
    $$PWD/model/functiondefinition.h \
    $$PWD/utils/templateextension.h

INCLUDEPATH += $$PWD

RESOURCES += \
    $$PWD/editorresources.qrc \
    $$PWD/editorresources.qrc

SUBDIRS += \
    $$PWD/src.pro
