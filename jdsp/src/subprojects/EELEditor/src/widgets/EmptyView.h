#ifndef EMPTYVIEW_H
#define EMPTYVIEW_H

#include <QWidget>

namespace Ui {
class EmptyView;
}

class EmptyView : public QWidget
{
    Q_OBJECT

public:
    explicit EmptyView(QList<QAction *> actions, QWidget *parent = nullptr);
    ~EmptyView();

private:
    Ui::EmptyView *ui;
};

#endif // EMPTYVIEW_H
