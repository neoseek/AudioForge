#ifndef ACTIONBUTTON_H
#define ACTIONBUTTON_H
#include <QAction>
#include <QPushButton>
/*!

* An extension of a QPushButton that supports QAction.
* This class represents a QPushButton extension that can be
* connected to an action and that configures itself depending
* on the status of the action.
* When the action changes its state, the button reflects
* such changes, and when the button is clicked the action
* is triggered.
*/
class ActionButton : public QPushButton {

   Q_OBJECT
private:

   // The action associated to this button.
   QAction *actionOwner = nullptr;
public:

   // Default constructor. Parent the widget parent of this button
   explicit ActionButton(QAction *action, QWidget *parent = nullptr);
   /*!
    * Set the action owner of this button, that is the action
    * associated to the button. The button is configured immediately
    * depending on the action status and the button and the action
    * are connected together so that when the action is changed the button
    * is updated and when the button is clicked the action is triggered.
    * action the action to associate to this button
    */
   void setAction(QAction *action);
public slots:

   /*!
    * Update the button status depending on a change
    * on the action status. This slot is invoked each time the action
    * "changed" signal is emitted.
    */
   void updateButtonStatusFromAction();
};

#endif // ACTIONBUTTON_H
