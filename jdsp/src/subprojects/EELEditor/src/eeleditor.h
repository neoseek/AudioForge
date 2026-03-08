#ifndef EELEDITOR_H
#define EELEDITOR_H

#include <QMainWindow>
#include "model/functiondefinition.h"
#include "model/annotationdefinition.h"
#include "model/customsymbolprovider.h"

#include "model/eelcompleter.h"
#include "model/eelhighlighter.h"

#include <DockManager.h>
#include <DockAreaWidget.h>
#include <DockWidget.h>

#ifdef HAS_JDSP_DRIVER
#include <IAudioService.h>
#endif

class ProjectView;
class FindReplaceForm;
class ConsoleOutput;
class QStackedWidget;
class EmptyView;
class VariableWatchWidget;

QT_BEGIN_NAMESPACE
namespace Ui { class EELEditor; }
QT_END_NAMESPACE

class EELEditor : public QMainWindow
{
    Q_OBJECT

public:
    EELEditor(QWidget *parent = nullptr);
    ~EELEditor();
    void openNewScript(QString path);
#ifdef HAS_JDSP_DRIVER
    void attachHost(IAudioService* _host);
#endif

signals:
    void scriptSaved(QString path);
    void executionRequested(QString path);

public slots:
    void onCompilerStarted(const QString& scriptName);
    void onCompilerFinished(int ret, const QString& retMsg, const QString& msg, const QString& scriptName, float initMs);
    void onConsoleOutputReceived(const QString& buffer);

    void newProject();
    void openProject();
    void saveProject();
    void saveProjectAs();
    void runCode();

    void goToLine();
    void jumpToFunction();

private slots:
    void onIsCodeLoadedChanged(bool isLoaded);
    void onCurrentFileUpdated(CodeContainer* prev, CodeContainer* code);
    void onBackendRefreshRequired();

protected:
    void closeEvent(QCloseEvent* ev) override;

private:
    Ui::EELEditor *ui;

    bool loadFallbackFont = false;

    QStackedWidget* codeView;
    CodeEditor* codeEdit;
    QWidget* codeWidget;
    EmptyView* emptyView;
    FindReplaceForm* findReplaceForm;

    ProjectView* projectView;
    CodeOutline* codeOutline;
    ConsoleOutput* consoleOutput;
    VariableWatchWidget* variableView;

    CustomSymbolProvider* symbolProvider;
    EELHighlighter* highlighter;
    EELCompleter* completer;

    bool ignoreErrorClearOnNextChangeEvent = false;

    ads::CDockManager* DockManager;
    ads::CDockAreaWidget* StatusDockArea;
    ads::CDockWidget* TimelineDockWidget;

#ifdef HAS_JDSP_DRIVER
    IAudioService* audioService = nullptr;
#endif

    void changeSyntaxStyle(QString def);
};
#endif // EELEDITOR_H
