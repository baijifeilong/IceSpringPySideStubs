# IceSpringPySideStubs

PySide stubs with Qt signals and Qt documentations and more.

Supported Qt versions now: PySide2 only.

## Official sites:

- Github: [https://github.com/baijifeilong/IceSpringPySideStubs](https://github.com/baijifeilong/IceSpringPySideStubs)
- Pypi(PySide2): [https://pypi.org/project/IceSpringPySideStubs-PySide2](https://pypi.org/project/IceSpringPySideStubs-PySide2)

## Features

- Qt official documentations support
- Qt signals support
- More correct type annotations
- Recognition of unknown method names
- Better performance: one class one file
- More editable: one class one file
- Clean: all codes are well formatted

## Known issues

- PySide6 support is not ready
- PyQt5 support is not ready
- PyQt6 support is not ready
- Unknown method name recognition not worked in PyCharm/IDEA

### Unknown method name recognition not worked in PyCharm/IDEA

You should remove PySide2 skeleton generated by PyCharm, and make the `PySide2` folder only-read to prevent regeneration.

## Install

- PySide2: `pip install IceSpringPySideStubs-PySide2`

## Usage

Out of the box

## Build

### Prerequisites:

Offline Qt document is required. If not, download one:

1. Install [Zeal](https://zealdocs.org/). `scoop install zeal` for Windows users.
2. Open `Zeal`, Download `Qt5` document from `Docsets`

### Build steps

1. `git clone https://github.com/baijifeilong/IceSpringPySideStubs`
2. `cd IceSpringPySideStubs`
3. `python -mvenv venv`
4. `./venv/Scripts/pip.exe install -r requirements.txt`
5. `vim main.py` Change `docRoot` if your `Qt` document wasn't downloaded by `scoop`+`zeal`
6. `./venv/Scripts/python.exe main.py` Generate stubs in `target` folder.
7. `./venv/Scripts/python.exe build.py` Generate `.whl` package in `target` folder.
8. `./venv/Scripts/pip.exe install __generated_whl_package__.whl` Install the `.whl` package

## Licence

GPL-3

## Example snippets

```python
import typing

import PySide2.QtCore


class QObject(object):
    """
    https://doc.qt.io/qt-5/qobject.html

    **Detailed Description**

    QObject is the heart of the Qt **Object Model** . The central feature in
    this model is a very powerful mechanism for seamless object communication
    called **signals and slots** . You can connect a signal to a slot with
    **connect** () and destroy the connection with **disconnect** (). To avoid
    never ending notification loops you can temporarily block signals with
    **blockSignals** (). The protected functions **connectNotify** () and
    **disconnectNotify** () make it possible to track connections.

    QObjects organize themselves in **object trees** . When you create a QObject
    with another object as parent, the object will automatically add itself to
    the parent\'s **children** () list. The parent takes ownership of the object;
    i.e., it will automatically delete its children in its destructor. You can
    look for an object by name and optionally type using **findChild** () or
    **findChildren** ().

    Every object has an **objectName** () and its class name can be found via
    the corresponding **metaObject** () (see **QMetaObject::className** ()). You
    can determine whether the object\'s class inherits another class in the
    QObject inheritance hierarchy by using the **inherits** () function.

    When an object is deleted, it emits a **destroyed** () signal. You can catch
    this signal to avoid dangling references to QObjects.

    QObjects can receive events through **event** () and filter the events of
    other objects. See **installEventFilter** () and **eventFilter** () for
    details. A convenience handler, **childEvent** (), can be reimplemented to
    catch child events.

    Last but not least, QObject provides the basic timer support in Qt; see
    **QTimer**  for high-level support for timers.

    Notice that the **Q_OBJECT**  macro is mandatory for any object that
    implements signals, slots or properties. You also need to run the **Meta
    Object Compiler**  on the source file. We strongly recommend the use of this
    macro in all subclasses of QObject regardless of whether or not they
    actually use signals, slots and properties, since failure to do so may lead
    certain functions to exhibit strange behavior.

    All Qt widgets inherit QObject. The convenience function **isWidgetType** ()
    returns whether an object is actually a widget. It is much faster than
    **qobject_cast** <**QWidget**  *>( **obj** ) or **obj** ->**inherits**
    ("**QWidget** ").

    Some QObject functions, e.g. **children** (), return a **QObjectList** .
    **QObjectList**  is a typedef for **QList** <QObject *>.

    **Thread Affinity**

    A QObject instance is said to have a **thread affinity** , or that it
    **lives** in a certain thread. When a QObject receives a **queued signal**
    or a **posted event** , the slot or event handler will run in the thread
    that the object lives in.

    **Note:** If a QObject has no thread affinity (that is, if **thread** ()
    returns zero), or if it lives in a thread that has no running event loop,
    then it cannot receive queued signals or posted events.

    By default, a QObject lives in the thread in which it is created. An
    object\'s thread affinity can be queried using **thread** () and changed
    using **moveToThread** ().

    All QObjects must live in the same thread as their parent. Consequently:

    * **setParent** () will fail if the two QObjects involved live in different
    threads.
      * When a QObject is moved to another thread, all its children
    will be automatically moved too.
      * **moveToThread** () will fail if the
    QObject has a parent.
      * If QObjects are created within **QThread::run**
    (), they cannot become children of the **QThread**  object because the
    **QThread**  does not live in the thread that calls **QThread::run** ().

    **Note:** A QObject\'s member variables **do not** automatically become its
    children. The parent-child relationship must be set by either passing a
    pointer to the child\'s **constructor** , or by calling **setParent** ().
    Without this step, the object\'s member variables will remain in the old
    thread when **moveToThread** () is called.

    **No Copy Constructor or Assignment Operator**

    QObject has neither a copy constructor nor an assignment operator. This is
    by design. Actually, they are declared, but in a `private` section with the
    macro **Q_DISABLE_COPY** (). In fact, all Qt classes derived from QObject
    (direct or indirect) use this macro to declare their copy constructor and
    assignment operator to be private. The reasoning is found in the discussion
    on **Identity vs Value**  on the Qt **Object Model**  page.

    The main consequence is that you should use pointers to QObject (or to your
    QObject subclass) where you might otherwise be tempted to use your QObject
    subclass as a value. For example, without a copy constructor, you can\'t use
    a subclass of QObject as the value to be stored in one of the container
    classes. You must store pointers.

    **Auto-Connection**

    Qt\'s meta-object system provides a mechanism to automatically connect
    signals and slots between QObject subclasses and their children. As long as
    objects are defined with suitable object names, and slots follow a simple
    naming convention, this connection can be performed at run-time by the
    **QMetaObject::connectSlotsByName** () function.

    **uic**  generates code that invokes this function to enable auto-connection
    to be performed between widgets on forms created with **Qt Designer**. More
    information about using auto-connection with **Qt Designer** is given in the
    **Using a Designer UI File in Your C++ Application**  section of the **Qt
    Designer** manual.

    **Dynamic Properties**

    From Qt 4.2, dynamic properties can be added to and removed from QObject
    instances at run-time. Dynamic properties do not need to be declared at
    compile-time, yet they provide the same advantages as static properties and
    are manipulated using the same API - using **property** () to read them and
    **setProperty** () to write them.

    From Qt 4.3, dynamic properties are supported by **Qt Designer** , and both
    standard Qt widgets and user-created forms can be given dynamic properties.

    **Internationalization (I18n)**

    All QObject subclasses support Qt\'s translation features, making it possible
    to translate an application\'s user interface into different languages.

    To make user-visible text translatable, it must be wrapped in calls to the
    **tr** () function. This is explained in detail in the **Writing Source Code
    for Translation**  document.

    **See also** **QMetaObject** , **QPointer** , **QObjectCleanupHandler** ,
    **Q_DISABLE_COPY** (), and **Object Trees & Ownership** .
    """

    def __init__(self, parent: typing.Optional[PySide2.QtCore.QObject] = ...) -> None:
        """
        https://doc.qt.io/qt-5/qobject.html#QObject

        **QObject::QObject(QObject * parent = nullptr)**

        Constructs an object with parent object **parent**.

        The parent of an object may be viewed as the object's owner. For
        instance, a **dialog box**  is the parent of the **OK** and **Cancel**
        buttons it contains.

        The destructor of a parent object destroys all child objects.

        Setting **parent** to `nullptr` constructs an object with no parent. If
        the object is a widget, it will become a top-level window.

        **Note:** This function can be invoked via the meta-object system and
        from QML. See **Q_INVOKABLE** .

        **See also** **parent** (), **findChild** (), and **findChildren** ().
        """
        ...

    def objectName(self) -> str:
        """
        https://doc.qt.io/qt-5/qobject.html#objectName-prop

        **objectName : QString**

        This property holds the name of this object

        You can find an object by name (and type) using **findChild** (). You
        can find a set of objects with **findChildren** ().

        **qDebug** ("MyClass::setPrecision(): (%s) invalid precision %f",
        **qPrintable** (objectName()), newPrecision);

        By default, this property contains an empty string.

        **Access functions:**

        QString **objectName** () const
        void **setObjectName** (const QString
        & **name** )

        **Notifier signal:**

        void ****objectNameChanged** ** (const QString & **objectName** )[see
        note below]

        **Note:** This is a private signal. It can be used in signal connections
        but cannot be emitted by the user.

        **See also** **metaObject** () and **QMetaObject::className** ().

        **Member Function Documentation**
        """
        ...

    def setObjectName(self, name: str) -> None:
        """
        https://doc.qt.io/qt-5/qobject.html#objectName-prop

        **objectName : QString**

        This property holds the name of this object

        You can find an object by name (and type) using **findChild** (). You
        can find a set of objects with **findChildren** ().

        **qDebug** ("MyClass::setPrecision(): (%s) invalid precision %f",
        **qPrintable** (objectName()), newPrecision);

        By default, this property contains an empty string.

        **Access functions:**

        QString **objectName** () const
        void **setObjectName** (const QString
        & **name** )

        **Notifier signal:**

        void ****objectNameChanged** ** (const QString & **objectName** )[see
        note below]

        **Note:** This is a private signal. It can be used in signal connections
        but cannot be emitted by the user.

        **See also** **metaObject** () and **QMetaObject::className** ().

        **Member Function Documentation**
        """
        ...

    @property
    def objectNameChanged(self) -> PySide2.QtCore.SignalInstance:
        """
        https://doc.qt.io/qt-5/qobject.html#objectNameChanged

        **[signal] void QObject::objectNameChanged(const QString & objectName
        )**

        This signal is emitted after the object's name has been changed. The new
        object name is passed as **objectName**.

        **Note:** This is a private signal. It can be used in signal connections
        but cannot be emitted by the user.

        **Note:** Notifier signal for property **objectName** .

        **See also** **QObject::objectName** .
        """
        ...

# More..........................................................................
# Line..........................................................................
# Here..........................................................................
# Are...........................................................................
# Omitted.......................................................................
```