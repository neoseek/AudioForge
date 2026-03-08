#include "newfilewizard.h"
#include "ui_newfilewizard.h"

#include <QDir>
#include <QFileDialog>
#include <QMessageBox>
#include <QRegularExpression>

NewFileWizard::NewFileWizard(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::NewFileWizard)
{
    ui->setupUi(this);

    // TODO
#ifdef Q_OS_LINUX
    ui->directory->setText(QDir::homePath() + "/.config/jamesdsp/liveprog");
#else
    ui->directory->setText(QDir::homePath());
#endif

    connect(ui->directorySelect, &QAbstractButton::clicked, [this]{
        QString dir = QFileDialog::getExistingDirectory(this, tr("Select directory"), ui->directory->text());
        if(dir.isEmpty())
            return;

        ui->directory->setText(dir);
    });
}

NewFileWizard::~NewFileWizard()
{
    delete ui;
}

void NewFileWizard::accept()
{
    if(!QDir(ui->directory->text()).exists())
    {
        QMessageBox::critical(this, tr("Error"), tr("Workspace directory does not exist"));
        return;
    }

    if(QFile(filePath()).exists())
    {
        QMessageBox::critical(this, tr("Error"), tr("A file with the same name already exists at this loction"));
        return;
    }

    QRegularExpression rx(R"(^(?!(?:COM[0-9]|CON|LPT[0-9]|NUL|PRN|AUX|com[0-9]|con|lpt[0-9]|nul|prn|aux)|\s|[\.]{2,})[^\\\/:*"?<>|]{1,254}(?<![\s\.])$)");
    if(!rx.match(ui->filename->text()).hasMatch() || ui->filename->text().length() <= 0)
    {
        QMessageBox::critical(this, tr("Error"), tr("File name is empty or contains illegal characters"));
        return;
    }

    QDialog::accept();
}

QString NewFileWizard::filePath() const
{
    return QDir::cleanPath(ui->directory->text() + QDir::separator() + ui->filename->text() + ".eel");
}

QString NewFileWizard::description() const
{
    return ui->description->text();
}
