#include "VariableWatchWidget.h"
#include "ui_VariableWatchWidget.h"

#include <IAudioService.h>
#include <QTimer>
#include <QMessageBox>
#include <QInputDialog>
#include <cfloat>

#include <model/VariableItemModel.h>

VariableWatchWidget::VariableWatchWidget(QWidget *parent) :
    QWidget(parent),
    ui(new Ui::VariableWatchWidget)
{
    ui->setupUi(this);

    variableWatchTimer = new QTimer(this);
    variableWatchTimer->setInterval(200);
    variableWatchTimer->setSingleShot(false);

    ui->variableView->setModel(new VariableItemModel(this));
    ui->variableView->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);

    connect(ui->refreshRate, qOverload<int>(&QSpinBox::valueChanged), this, &VariableWatchWidget::onRefreshValueChanged);
    connect(ui->variableView, &QTableView::clicked, this, &VariableWatchWidget::onVariableClicked);
}

VariableWatchWidget::~VariableWatchWidget()
{
    delete ui;
}

#ifdef HAS_JDSP_DRIVER
void VariableWatchWidget::attachHost(IAudioService *_host)
{
    audioService = _host;

    connect(audioService, &IAudioService::eelVariablesEnumerated, static_cast<VariableItemModel*>(ui->variableView->model()), &VariableItemModel::onLiveprogVariablesUpdated);
    connect(variableWatchTimer, &QTimer::timeout, audioService, &IAudioService::enumerateLiveprogVariables);
}
#endif

void VariableWatchWidget::setWatching(bool enabled)
{
    enabled ? variableWatchTimer->start() : variableWatchTimer->stop();
}

void VariableWatchWidget::onRefreshValueChanged(int value)
{
    variableWatchTimer->setInterval(value);
}

void VariableWatchWidget::onVariableClicked(const QModelIndex &index)
{
    if(!index.isValid())
        return;

    auto* model = static_cast<VariableItemModel*>(ui->variableView->model());
    auto variable = model->variableAtIndex(index);

    if(variable.name.empty())
    {
        return;
    }

    if(variable.isString)
    {
        QMessageBox::critical(this, tr("Error"), tr("This variable is a string. Currently only numerical value types can be modified."));
        return;
    }

    bool ok = false;
    double value = QInputDialog::getDouble(this, tr("Manipulate variable"),
                            tr("Enter a new value for variable '%1':").arg(variable.name.c_str()), std::get<float>(variable.value), FLT_MIN, FLT_MAX, 7, &ok);
    if(!ok)
    {
        return;
    }

    if(!audioService->host()->manipulateEelVariable(variable.name.c_str(), value))
    {
        QMessageBox::critical(this, tr("Error"), tr("Failed to manipulate variable '%1'. Either it does not exist anymore, or it cannot be changed.").arg(variable.name.c_str()));
    }
}
