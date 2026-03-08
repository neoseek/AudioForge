#include "eeleditor.h"
#include "ui_eeleditor.h"

#include "utils/FontUtils.h"
#include "widgets/findreplaceform.h"
#include "widgets/projectview.h"
#include "widgets/consoleoutput.h"
#include "widgets/proxystyle.h"
#include "widgets/dialog/newfilewizard.h"

#include <QFile>
#include <QMap>
#include <QListWidgetItem>
#include <QSyntaxStyle.hpp>
#include <QDebug>
#include <QDir>
#include <QFileDialog>
#include <QInputDialog>
#include <QVBoxLayout>
#include <QDesktopServices>
#include <QDateTime>
#include <QMessageBox>
#include <QStackedWidget>
#include <QLabel>
#include <QPushButton>
#include <QHeaderView>

#include <DockAreaTitleBar.h>
#include <DockAreaTabBar.h>
#include <FloatingDockContainer.h>
#include <DockComponentsFactory.h>

#include <widgets/ActionButton.h>
#include <widgets/EmptyView.h>
#include <widgets/VariableWatchWidget.h>

#include <model/VariableItemModel.h>

using namespace ads;

#define SET_DOCK_ICON(dock,icon) \
    auto* dock##Action = dock->toggleViewAction(); \
    dock##Action->setIcon(QIcon(icon));

EELEditor::EELEditor(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::EELEditor)
{
    this->setStyle(new ProxyStyle("Fusion"));

    ui->setupUi(this);
    this->layout()->setMenuBar(ui->menuBar);

    codeEdit = new CodeEditor(this);
    findReplaceForm = new FindReplaceForm(this);
    projectView = new ProjectView(this);
    codeOutline = new CodeOutline(this);
    consoleOutput = new ConsoleOutput(loadFallbackFont, this);

    variableView = new VariableWatchWidget(this);

    codeView = new QStackedWidget(this);

    emptyView = new EmptyView(QList<QAction*>(std::initializer_list<QAction*>(
                                                  {ui->actionNew, ui->actionOpen_file})), this);
    codeWidget = new QWidget(this);
    auto* codeLayout = new QVBoxLayout(codeWidget);
    codeLayout->setContentsMargins(0, 0, 0, 0);
    codeLayout->addWidget(codeEdit);
    codeLayout->addWidget(findReplaceForm);

    codeView->addWidget(codeWidget);
    codeView->addWidget(emptyView);

    CDockManager::setConfigFlag(CDockManager::OpaqueSplitterResize, true);
    CDockManager::setConfigFlag(CDockManager::XmlCompressionEnabled, false);
    CDockManager::setConfigFlag(CDockManager::FocusHighlighting, true);
    DockManager = new CDockManager(this);

    CDockWidget* CentralDockWidget = new CDockWidget("CentralWidget");
    CentralDockWidget->setMinimumSize(0,0);
    CentralDockWidget->setWidget(codeView);
    auto* CentralDockArea = DockManager->setCentralWidget(CentralDockWidget);
    CentralDockWidget->setMinimumSizeHintMode(CDockWidget::MinimumSizeHintFromContent);
    CentralDockArea->setAllowedAreas(DockWidgetArea::OuterDockAreas);

    CDockWidget* projectsDock = new CDockWidget(tr("Loaded projects"));
    projectsDock->setWidget(projectView);
    projectsDock->setMinimumSizeHintMode(CDockWidget::MinimumSizeHintFromDockWidget);
    projectsDock->resize(250, 50);
    projectsDock->setMinimumSize(200,5);
    projectsDock->setGeometry(0,0,0,400);
    SET_DOCK_ICON(projectsDock,":/icons/ListFolder_16x.svg")
    auto* leftArea = DockManager->addDockWidget(DockWidgetArea::LeftDockWidgetArea, projectsDock);
    ui->menuView->addAction(projectsDock->toggleViewAction());

    auto* outlineDock = new CDockWidget(tr("Code outline"));
    outlineDock->setWidget(codeOutline);
    outlineDock->setMinimumSizeHintMode(CDockWidget::MinimumSizeHintFromDockWidget);
    outlineDock->resize(250, 150);
    outlineDock->setMinimumSize(200,5);
    SET_DOCK_ICON(outlineDock,":/icons/JSONDocumentOutline_16x.svg")
    DockManager->addDockWidget(DockWidgetArea::BottomDockWidgetArea, outlineDock, leftArea);
    ui->menuView->addAction(outlineDock->toggleViewAction());

#ifdef HAS_JDSP_DRIVER
    auto* variableDock = new CDockWidget(tr("Variable view"));
    variableDock->setWidget(variableView);
    variableDock->setMinimumSizeHintMode(CDockWidget::MinimumSizeHintFromDockWidget);
    variableDock->resize(400, 150);
    variableDock->setMinimumSize(200,5);
    DockManager->addDockWidget(DockWidgetArea::RightDockWidgetArea, variableDock);
    variableDock->toggleView(false);
    SET_DOCK_ICON(variableDock,":/icons/DataPreview.svg")
    ui->toolBar->addAction(variableDock->toggleViewAction());
    ui->menuView->addAction(variableDock->toggleViewAction());

    connect(variableDock, &CDockWidget::viewToggled, variableView, &VariableWatchWidget::setWatching);
#endif

    auto* consoleDock = new CDockWidget(tr("Console output"));
    consoleDock->setWidget(consoleOutput);
    consoleDock->setMinimumSizeHintMode(CDockWidget::MinimumSizeHintFromDockWidget);
    consoleDock->resize(250, 150);
    consoleDock->setMinimumSize(50,150);
    SET_DOCK_ICON(consoleDock,":/icons/Console_16x.svg")
    DockManager->addDockWidget(DockWidgetArea::BottomDockWidgetArea, consoleDock);
    ui->menuView->addAction(consoleDock->toggleViewAction());

    findReplaceForm->setTextEdit(codeEdit);
    findReplaceForm->hide();

    completer = new EELCompleter();
    highlighter = new EELHighlighter();
    symbolProvider = new CustomSymbolProvider();

    symbolProvider->setLanguageSpecs(completer,highlighter);
    symbolProvider->setCodeEditorModule(codeEdit);
    symbolProvider->setCodeOutlineModule(codeOutline);
    symbolProvider->connectSignals();

    codeEdit->setFont(FontUtils::preferredMonospaceFont());
    codeEdit->setCompleter(completer);
    codeEdit->setHighlighter(highlighter);
    codeEdit->setUndoRedoEnabled(true);
    changeSyntaxStyle(":/definitions/drakula.xml");

    symbolProvider->reloadSymbols();

    onIsCodeLoadedChanged(false);
    ui->actionUndo->setEnabled(false);
    ui->actionRedo->setEnabled(false);

    connect(codeEdit, &CodeEditor::undoAvailable, ui->actionUndo, &QAction::setEnabled);
    connect(codeEdit, &CodeEditor::redoAvailable, ui->actionRedo, &QAction::setEnabled);
    connect(codeEdit, &CodeEditor::backendRefreshRequired, this, &EELEditor::onBackendRefreshRequired);

    connect(findReplaceForm, &FindReplaceForm::closedPressed, findReplaceForm, &FindReplaceForm::hide);

    connect(projectView,&ProjectView::currentFileUpdated, this, &EELEditor::onCurrentFileUpdated);

    connect(ui->actionRun_code, &QAction::triggered, this, &EELEditor::runCode);
    connect(ui->actionNew, &QAction::triggered,this, &EELEditor::newProject);
    connect(ui->actionOpen_file, &QAction::triggered, this, &EELEditor::openProject);
    connect(ui->actionClose_filw, &QAction::triggered, projectView, &ProjectView::closeCurrentFile);
    connect(ui->actionSave, &QAction::triggered, this, &EELEditor::saveProject);
    connect(ui->actionSave_as, &QAction::triggered, this, &EELEditor::saveProjectAs);
    connect(ui->actionUndo, &QAction::triggered,codeEdit, &QCodeEditor::undo);
    connect(ui->actionRedo, &QAction::triggered,codeEdit, &QCodeEditor::redo);
    connect(ui->actionFind_Replace, &QAction::triggered, findReplaceForm, &FindReplaceForm::toggle);
    connect(ui->actionGo_to_line, &QAction::triggered, this, &EELEditor::goToLine);
    connect(ui->actionJump_to_function, &QAction::triggered, this, &EELEditor::jumpToFunction);
    connect(ui->actionGo_to_init, &QAction::triggered, [this]{
        codeOutline->goToAnnotation("@init");
    });
    connect(ui->actionGo_to_sample, &QAction::triggered, [this]{
        codeOutline->goToAnnotation("@sample");
    });
    connect(ui->actionEEL2_documentation, &QAction::triggered, []{
        QDesktopServices::openUrl(QUrl("https://github.com/james34602/EEL_VM"));
    });
}

EELEditor::~EELEditor()
{
    delete ui;
}

void EELEditor::openNewScript(QString path){
    projectView->addFile(path);
}

#ifdef HAS_JDSP_DRIVER
void EELEditor::attachHost(IAudioService *_host)
{
    audioService = _host;

    connect(audioService, &IAudioService::eelCompilationStarted, this, &EELEditor::onCompilerStarted);
    connect(audioService, &IAudioService::eelCompilationFinished, this, &EELEditor::onCompilerFinished);
    connect(audioService, &IAudioService::eelOutputReceived, this, &EELEditor::onConsoleOutputReceived);
    connect(ui->actionFreeze, &QAction::toggled, [this](bool state){ audioService->host()->freezeLiveprogExecution(state); });

    this->variableView->attachHost(audioService);
}
#endif

void EELEditor::onCompilerStarted(const QString &scriptName)
{
    Q_UNUSED(scriptName)
    consoleOutput->clear();
    consoleOutput->printLowPriorityLine(tr("'%1' started compiling at %2").arg(QFileInfo(scriptName).fileName()).arg(QDateTime::currentDateTime().toString("hh:mm:ss.zzz")));
}

void EELEditor::onCompilerFinished(int ret, const QString& retMsg, const QString& msg, const QString& scriptName, float initMs)
{

    int line = -1;

    if(ret <= 0)
    {
        QString message = msg;

        QRegularExpression linenumRe(R"(^(\d+):)");
        auto matchIterator = linenumRe.globalMatch(msg);
        if(matchIterator.hasNext()){
            auto match = matchIterator.next();
            bool ok;
            line = match.captured(1).toInt(&ok);
            if(!ok)
            {
                line = -1;
            }

            message = message.remove(0, match.capturedLength(0));
        }

        consoleOutput->clear();
        consoleOutput->printErrorLine(QString("%1 in '%2'<br>").arg(retMsg).arg(QFileInfo(scriptName).fileName()));

        auto findAnnotationLineExternal = [](const QString& path, const QString& name){
            QRegularExpression function(R"((^|(?<=\n))(\@[^\s\W]*))");
            int linenum = 1;

            QFile inputFile(path);
            if (inputFile.open(QIODevice::ReadOnly))
            {
               QTextStream in(&inputFile);
               while (!in.atEnd())
               {
                  QString line = in.readLine();
                  auto matchIterator = function.globalMatch(line);
                  if(matchIterator.hasNext()){

                      auto match = matchIterator.next();
                      if(line == name)
                      {
                          return linenum;
                      }
                  }
                  linenum++;
               }
               inputFile.close();
            }

            return -1;
        };

        int initLine = findAnnotationLineExternal(scriptName, "@init");
        int sampleLine = findAnnotationLineExternal(scriptName,"@sample");
        if(ret == -1) // error in @init
        {
            if(initLine >= 0)
                line += initLine;
            else
                line = -1;
        }
        else if(ret == -3) // error in @sample
        {
            if(sampleLine >= 0)
                line += sampleLine;
            else
                line = -1;
        }

        if(line >= 0)
        {
            consoleOutput->printErrorLine(QString("Line %1:%2").arg(line).arg(message));
        }
        else
        {
            consoleOutput->printErrorLine(msg);
        }

        consoleOutput->printLowPriorityLine(tr("<br>Compilation stopped at %2").arg(QDateTime::currentDateTime().toString("hh:mm:ss.zzz")));
    }
    else
    {
        consoleOutput->printLowPriorityLine(tr("Script initialization took %1ms").arg(initMs));
    }

    auto* cc = projectView->getCurrentFile();
    if(cc == nullptr)
    {
        return;
    }

    // Don't highlight if different script is opened in editor
    if(QFileInfo(scriptName) != QFileInfo(cc->path))
        return;

    if(line < 0)
        highlighter->setErrorLine(-1);
    else
        highlighter->setErrorLine(line - 1);

    ignoreErrorClearOnNextChangeEvent = true;
    codeEdit->updateStyle();
}

void EELEditor::onConsoleOutputReceived(const QString &buffer)
{
    consoleOutput->print(buffer);
}

void EELEditor::onCurrentFileUpdated(CodeContainer *prev, CodeContainer *code)
{
    Q_UNUSED(prev)

    if(code != nullptr)
    {
        codeEdit->loadCode(code);
    }

    onIsCodeLoadedChanged(code != nullptr);
}

void EELEditor::onBackendRefreshRequired()
{
    if(ignoreErrorClearOnNextChangeEvent)
    {
        ignoreErrorClearOnNextChangeEvent = false;
        return;
    }

    highlighter->setErrorLine(-1);
    highlighter->rehighlight();
}

void EELEditor::closeEvent(QCloseEvent *ev)
{
    /* Unfreeze on close */
    ui->actionFreeze->setChecked(false);
    audioService->host()->freezeLiveprogExecution(false);

    QMainWindow::closeEvent(ev);
}

void EELEditor::onIsCodeLoadedChanged(bool isLoaded)
{
    ui->actionSave->setEnabled(isLoaded);
    ui->actionSave_as->setEnabled(isLoaded);
    ui->actionClose_filw->setEnabled(isLoaded);
    ui->actionRun_code->setEnabled(isLoaded);
    ui->actionFind_Replace->setEnabled(isLoaded);
    ui->actionGo_to_init->setEnabled(isLoaded);
    ui->actionGo_to_sample->setEnabled(isLoaded);
    ui->actionGo_to_line->setEnabled(isLoaded);
    ui->actionJump_to_function->setEnabled(isLoaded);
    codeEdit->setEnabled(isLoaded);

    codeView->setCurrentIndex(isLoaded ? 0 : 1);
}

void EELEditor::newProject()
{
    auto* newFileWiz = new NewFileWizard(this);

    if(newFileWiz->exec())
    {
        QFile file(newFileWiz->filePath());
        file.open(QIODevice::WriteOnly);

        if(!file.isOpen())
        {
            QMessageBox::critical(this, tr("Error"), tr("Cannot write file"));
            return;
        }

        QString desc = newFileWiz->description();
        QTextStream stream(&file);
        if(!desc.isEmpty())
        {
            stream << "desc: " << desc << "\n";
        }
        stream << "\n";
        stream << "@init\n"
                  "// Prepare variables here\n"
                  "\n";
        stream << "@sample\n"
                  "// Access and modify audio samples here\n"
                  "spl0 = spl0;\n"
                  "spl1 = spl1;\n";
        file.close();

        projectView->addFile(newFileWiz->filePath());
    }

    newFileWiz->deleteLater();
}

void EELEditor::openProject()
{
    QString fileName = QFileDialog::getOpenFileName(this, tr("Open EEL script"), "", tr("EEL2 Script (*.eel)"));

    if(fileName.isEmpty())
    {
        return;
    }
    projectView->addFile(fileName);
}

void EELEditor::saveProject()
{
    projectView->getCurrentFile()->code = codeEdit->toPlainText();
    projectView->getCurrentFile()->save("", this);
    emit scriptSaved(projectView->getCurrentFile()->path);
}

void EELEditor::saveProjectAs()
{
    QString fileName = QFileDialog::getSaveFileName(this, tr("Save as"), projectView->getCurrentFile()->path, "EEL2 script (*.eel)");

    if (fileName.isEmpty())
    {
        return;
    }

    projectView->getCurrentFile()->code = codeEdit->toPlainText();
    projectView->getCurrentFile()->save(fileName, this);
    emit scriptSaved(fileName);
}

void EELEditor::runCode()
{
    CodeContainer* cc = projectView->getCurrentFile();
    if(cc == nullptr)
    {
        QMessageBox::critical(this, tr("Cannot execute"), tr("No script file opened. Please open one first and try again."));
        return;
    }

    saveProject();
    emit executionRequested(projectView->getCurrentFile()->path);
}

void EELEditor::goToLine()
{
    bool ok = true;
    int line = QInputDialog::getInt(this, tr("Go to line..."),
                         tr("Enter line number:"), codeEdit->getCurrentLine(), 1, 2147483647, 1, &ok);
    if (ok && line >= 0)
    {
        codeEdit->goToLine(line);
    }
}

void EELEditor::jumpToFunction()
{
    bool ok = true;
    QString name = QInputDialog::getText(this, tr("Jump to function..."),
                             tr("Enter function name:") , QLineEdit::Normal, "", &ok);
    if (ok && !name.isEmpty())
    {
        codeOutline->goToFunction(name);
    }
}

void EELEditor::changeSyntaxStyle(QString def)
{
    // Workaround to solve stylesheet conflicts
    DockManager->setStyleSheet("");
    codeEdit->loadStyle(def);

    QString Result;
    QString FileName = ":ads/stylesheets/";
    FileName += CDockManager::testConfigFlag(CDockManager::FocusHighlighting)
        ? "focus_highlighting" : "default";
#ifdef Q_OS_LINUX
    FileName += "_linux";
#endif
    FileName += ".css";
    QFile StyleSheetFile(FileName);
    StyleSheetFile.open(QIODevice::ReadOnly);
    QTextStream StyleSheetStream(&StyleSheetFile);
    Result = StyleSheetStream.readAll();
    StyleSheetFile.close();
    DockManager->setStyleSheet(Result);
}
