#ifndef CODECONTAINER_H
#define CODECONTAINER_H

#include "qdebug.h"
#include <QFile>
#ifndef HEADLESS
#include <QMessageBox>
#endif
#include <QString>
#include <QTextStream>

class CodeContainer
{
public:
    CodeContainer(){}
    CodeContainer(QString _path){
        path = _path;
        reloadCode();
    };
    void reloadCode(){
        codeLoaded = true;
        QFile fl(path);
        if (!fl.open(QIODevice::ReadOnly))
            return;
        code = fl.readAll();
    }
    void save(QString cpath = "", QWidget* parent = nullptr){
        if(cpath.isEmpty())
            cpath = path;

        QFile file(cpath);
        if(file.open(QIODevice::WriteOnly | QIODevice::Text))
        {
            QTextStream stream(&file);
            stream << code;
            file.close();
        }
        else {
#ifndef HEADLESS
            if(parent != nullptr)
                QMessageBox::warning(parent, "File error", "Failed to save script. Reason: " + file.errorString());
#endif
            qWarning().noquote().nospace() << "Failed to save eel script to " << cpath;
            qWarning().noquote().nospace() << "Error code: " << file.error() << "; reason: " << file.errorString();
        }
    };

    bool codeLoaded = false;
    QString code;
    QString path;
};

Q_DECLARE_METATYPE(CodeContainer*);

#endif // CODECONTAINER_H
