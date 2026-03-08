#ifndef VARIABLEITEMMODEL_H
#define VARIABLEITEMMODEL_H

#include <QAbstractTableModel>

#ifdef HAS_JDSP_DRIVER
#include <EelVariable.h>
#endif

class VariableItemModel : public QAbstractTableModel
{
    Q_OBJECT

public:
    explicit VariableItemModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    int columnCount(const QModelIndex &parent = QModelIndex()) const override;

    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;

#ifdef HAS_JDSP_DRIVER
    EelVariable variableAtIndex(const QModelIndex &index) const;
#endif

public slots:
#ifdef HAS_JDSP_DRIVER
    void onLiveprogVariablesUpdated(const std::vector<EelVariable>& vars);
#endif

private:
#ifdef HAS_JDSP_DRIVER
    std::vector<EelVariable> variables;
#endif
};

#endif // VARIABLEITEMMODEL_H
