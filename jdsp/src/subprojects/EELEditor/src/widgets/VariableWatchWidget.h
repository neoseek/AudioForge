#ifndef VARIABLEWATCHWIDGET_H
#define VARIABLEWATCHWIDGET_H

#include <QWidget>

class QTimer;
class IAudioService;

namespace Ui {
class VariableWatchWidget;
}

class VariableWatchWidget : public QWidget
{
    Q_OBJECT

public:
    explicit VariableWatchWidget(QWidget *parent = nullptr);
    ~VariableWatchWidget();

#ifdef HAS_JDSP_DRIVER
    void attachHost(IAudioService *_host);
#endif

public slots:
    void setWatching(bool enabled);

private slots:
    void onRefreshValueChanged(int value);
    void onVariableClicked(const QModelIndex& index);

private:
    Ui::VariableWatchWidget *ui;
    IAudioService* audioService = nullptr;
    QTimer* variableWatchTimer;

};

#endif // VARIABLEWATCHWIDGET_H
