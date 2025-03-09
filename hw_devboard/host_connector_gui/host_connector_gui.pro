CONFIG += c++20

HEADERS = \
    DisplayWidget.h \
    ImageProcessor.h \
    MainWindow.h \
    Synchronizer.h \
    TcpServer.h \
    UsbContext.h \
    UsbDevice.h \
    VideoChip.h

SOURCES = \
    main.cpp \
    DisplayWidget.cpp \
    ImageProcessor.cpp \
    MainWindow.cpp \
    Synchronizer.cpp \
    TcpServer.cpp \
    UsbContext.cpp \
    UsbDevice.cpp \
    VideoChip.cpp

FORMS = \
    MainWindow.ui

QT += \
    network \
    widgets

LIBS += \
    -lusb-1.0
