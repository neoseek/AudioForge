#include "EmptyView.h"
#include "ui_EmptyView.h"

#include "ActionButton.h"

EmptyView::EmptyView(QList<QAction*> actions, QWidget *parent) :
    QWidget(parent),
    ui(new Ui::EmptyView)
{
    ui->setupUi(this);

    for(auto* action : actions)
    {
        ui->actionLayout->insertWidget(ui->actionLayout->count() - 1, new ActionButton(action, this));
    }
}

EmptyView::~EmptyView()
{
    delete ui;
}
