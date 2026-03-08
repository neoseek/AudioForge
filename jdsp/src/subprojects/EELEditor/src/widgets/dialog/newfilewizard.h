#ifndef NEWFILEWIZARD_H
#define NEWFILEWIZARD_H

#include <QDialog>

namespace Ui {
class NewFileWizard;
}

class NewFileWizard : public QDialog
{
    Q_OBJECT

public:
    explicit NewFileWizard(QWidget *parent = nullptr);
    ~NewFileWizard();

    void accept() override;

    QString filePath() const;
    QString description() const;

private:
    Ui::NewFileWizard *ui;
};

#endif // NEWFILEWIZARD_H
