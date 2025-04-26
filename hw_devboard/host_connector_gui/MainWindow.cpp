#include "MainWindow.h"

#include <QActionGroup>
#include <QInputDialog>
#include <QMessageBox>

#include "ui_MainWindow.h"

MainWindow::MainWindow(UsbContext *usbContext, QWidget *parent)
    : QMainWindow(parent), m_usbContext(usbContext) {
  m_ui = new Ui_MainWindow();
  m_ui->setupUi(this);

  m_ui->actionQuit->setShortcut(QKeySequence::Quit);
  m_ui->actionViewFullscreen->setShortcut(QKeySequence::FullScreen);

  QActionGroup *paletteGroup = new QActionGroup(this);
  for (QAction *action : m_ui->menuViewPalette->actions()) {
    action->setActionGroup(paletteGroup);
    action->setCheckable(true);
  }
  m_ui->actionViewPaletteRedGreenBlueInsert->setChecked(true);

  m_usbDevice = new UsbDeviceShim(this);
  m_synchonizer = new Synchronizer(this);
  m_imageProcessor = new ImageProcessor(this);

  connect(m_usbDevice, &UsbDeviceShim::isConnectedChanged, this,
          &MainWindow::isConnectedChanged);
  connect(m_usbDevice, &UsbDeviceShim::failed, this,
          &MainWindow::showDeviceError, Qt::QueuedConnection);
  connect(m_usbDevice, &UsbDeviceShim::newSamples, this,
          [this](QByteArrayView samples) {
            m_synchonizer->pushSamples(samples,
                                       *m_usbDevice->videoChipChannels());
          });
  connect(m_synchonizer, &Synchronizer::imageReceived, this,
          &MainWindow::processReceivedImage);

  m_tcpServer = new TcpServer(m_usbDevice, m_imageProcessor, this);

  // Set the window's right-click menu actions.
  addAction(m_ui->actionViewHideMenuBar);

  // Connect menu actions to their handlers.
  connect(m_ui->actionDeviceConnect, &QAction::triggered, this,
          &MainWindow::connectDevice);
  connect(m_ui->actionDeviceDisconnect, &QAction::triggered, m_usbDevice,
          &UsbDeviceShim::disconnectDevice);
  connect(m_ui->actionDeviceProperties, &QAction::triggered, this,
          &MainWindow::showDevicePropertiesModal);
  connect(m_ui->actionDeviceControlServer, &QAction::toggled, this,
          &MainWindow::tcpServerToggled);
  connect(m_ui->actionQuit, &QAction::triggered, &QApplication::quit);
  connect(m_ui->actionViewScale, &QAction::toggled, this,
          &MainWindow::applyZoom);
  connect(m_ui->actionViewFullscreen, &QAction::toggled, this,
          &MainWindow::applyFullscreen);
  connect(m_ui->actionPresetHelloWorld40, &QAction::triggered, this,
          &MainWindow::execPresetHelloWorld40);
  connect(m_ui->actionPresetHelloWorld80, &QAction::triggered, this,
          &MainWindow::execPresetHelloWorld80);
  connect(m_ui->actionPresetUniformColor, &QAction::triggered, this,
          &MainWindow::execPresetUniformColor);
  connect(m_ui->actionPresetColorBands, &QAction::triggered, this,
          &MainWindow::execPresetColorBands);

  // Forcefully set some initial UI state by simulating the respective events.
  applyZoom();
  isConnectedChanged();
}

MainWindow::~MainWindow() {
  delete m_usbDevice;
  delete m_ui;
}

void MainWindow::connectDevice() {
  UsbContext::DeviceHandle device = m_usbContext->findOurDevice();
  m_usbDevice->connectDevice(std::move(device));
}

void MainWindow::isConnectedChanged() {
  bool isConnected = m_usbDevice->isConnected();

  m_synchonizer->reset();
  m_imageProcessor->setInputImage(QImage(), VideoChipType::EF9345,
                                  VideoChipChannelMapping{},
                                  VIDEO_MODE_40_COLUMNS); // clear

  m_ui->actionDeviceConnect->setEnabled(!isConnected);
  m_ui->actionDeviceDisconnect->setEnabled(isConnected);
  m_ui->actionDeviceProperties->setEnabled(isConnected);

  for (QAction *action : m_ui->menuViewPalette->actions()) {
    action->setEnabled(isConnected);
  }

  for (QAction *action : m_ui->menuPreset->actions()) {
    action->setEnabled(isConnected);
  }

  if (isConnected) {
    m_ui->displayWidget->setContentsText("Synchronizing to signal...");
  } else {
    m_ui->displayWidget->setContentsText("No device connected");
  }
}

void MainWindow::showDeviceError(UsbDevice::Error error) {
  switch (error) {
  case UsbDevice::Error::DeviceInUseError:
    QMessageBox::critical(this, "USB device error", "Device already in use.");
    break;
  case UsbDevice::Error::IoError:
    QMessageBox::critical(this, "USB device error", "I/O error.");
    break;
  case UsbDevice::Error::NoVideoChipDetected:
    QMessageBox::critical(
        this, "Unusable USB device detected",
        "The connected USB board did not detect a video chip.");
    break;
  }
}

void MainWindow::showDevicePropertiesModal() {
  QString chipType;
  switch (*m_usbDevice->videoChipType()) {
  case EF9345:
    chipType = "EF9345";
    break;
  case TS9347:
    chipType = "TS9347";
    break;
  }

  QString details = "Text mode:\n";
  switch (*m_usbDevice->videoChipMode()) {
  case VIDEO_MODE_40_COLUMNS:
    details += "40 columns";
    break;
  case VIDEO_MODE_80_COLUMNS:
    details += "80 columns";
    break;
  }

  VideoChipChannelMapping map = *m_usbDevice->videoChipChannels();
  details += "\n\nAvailable channels:";
  if (map.red_mask != 0) {
    details += QString::asprintf("\n- R %#04x", (uint8_t)map.red_mask);
  }
  if (map.green_mask != 0) {
    details += QString::asprintf("\n- G %#04x", (uint8_t)map.green_mask);
  }
  if (map.blue_mask != 0) {
    details += QString::asprintf("\n- B %#04x", (uint8_t)map.blue_mask);
  }
  if (map.insert_mask != 0) {
    details += QString::asprintf("\n- I %#04x", (uint8_t)map.insert_mask);
  }
  if (map.hvs_mask != 0) {
    details += QString::asprintf("\n- HVS %#04x", (uint8_t)map.hvs_mask);
  }

  QMessageBox msgBox(QMessageBox::Icon::Information, "Device properties",
                     "Chip type: " + chipType, QMessageBox::StandardButton::Ok,
                     this);
  msgBox.setDetailedText(details);
  msgBox.exec();
}

void MainWindow::tcpServerToggled() {
  if (m_ui->actionDeviceControlServer->isChecked()) {
    bool ok = false;
    QString result =
        QInputDialog::getText(this, "TCP Server", "Listen address",
                              QLineEdit::Normal, m_tcpServerInputText, &ok);
    if (!ok) {
      // Canceled by user.
    canceled:
      m_ui->actionDeviceControlServer->setChecked(false);
      return;
    }

    // Remember the input, so that it's redisplayed if the dialog is sown again.
    m_tcpServerInputText = result;

    QHostAddress address;
    uint16_t port;
    if (!TcpServer::parseAddressAndPort(result, &address, &port)) {
      m_ui->actionDeviceControlServer->setChecked(false);
      QMessageBox::critical(this, "TCP Server", "Invalid listen address.");
      goto canceled;
    }

    QString errorText;
    if (!m_tcpServer->startListening(address, port, &errorText)) {
      QMessageBox::critical(this, "TCP Server", errorText);
      goto canceled;
    }
  } else {
    m_tcpServer->stopListening();
  }
}

void MainWindow::applyZoom() {
  m_ui->displayWidget->setScalingEnabled(m_ui->actionViewScale->isChecked());
}

void MainWindow::applyFullscreen() {
  if (m_ui->actionViewFullscreen->isChecked()) {
    setWindowState(windowState() | Qt::WindowFullScreen);
  } else {
    setWindowState(windowState() & ~Qt::WindowFullScreen);
  }
}

void MainWindow::processReceivedImage(QImage image) {
  m_imageProcessor->setInputImage(image, *m_usbDevice->videoChipType(),
                                  *m_usbDevice->videoChipChannels(),
                                  *m_usbDevice->videoChipMode());

  QImage (ImageProcessor::*uncropped)() const;
  QImage (ImageProcessor::*cropped)() const;

  if (m_ui->actionViewPaletteRedGreenBlueInsert->isChecked()) {
    uncropped = &ImageProcessor::rgbInsertUncroppedImage;
    cropped = &ImageProcessor::rgbInsertCroppedImage;
  } else if (m_ui->actionViewPaletteRedGreenBlue->isChecked()) {
    uncropped = &ImageProcessor::rgbUncroppedImage;
    cropped = &ImageProcessor::rgbCroppedImage;
  } else if (m_ui->actionViewPaletteGrayscale->isChecked()) {
    uncropped = &ImageProcessor::grayscaleUncroppedImage;
    cropped = &ImageProcessor::grayscaleCroppedImage;
  } else if (m_ui->actionViewPaletteInsert->isChecked()) {
    uncropped = &ImageProcessor::insertUncroppedImage;
    cropped = &ImageProcessor::insertCroppedImage;
  } else {
    abort(); // one of the above must be selected
  }

  QImage result;
  if (m_ui->actionViewCrop->isChecked()) {
    result = (m_imageProcessor->*cropped)();
  } else {
    result = (m_imageProcessor->*uncropped)();
  }

  m_ui->displayWidget->setContentsImage(result);
}

bool MainWindow::waitNotBusy() {
  // Iterate up to a maximum number of iterations.
  for (size_t i = 0; i < 10000; ++i) {
    std::optional<uint8_t> status = m_usbDevice->busRead(REG_R0);
    if (!status) {
      break;
    } else if ((*status & 0x80) == 0) {
      return true;
    }
  }
  return false;
}

void MainWindow::execPresetHelloWorld40() {
  m_usbDevice->busWrite(REG_ER0, 0x91); // nop
  waitNotBusy();

  if (m_usbDevice->videoChipType() == VideoChipType::EF9345) {
    m_usbDevice->busWrite(REG_R1, 0x10);
  } else {
    m_usbDevice->busWrite(REG_R1, 0x00);
  }
  m_usbDevice->busWrite(REG_ER0, 0x81); // tgs
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x67);
  m_usbDevice->busWrite(REG_ER0, 0x83); // pat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x00);
  m_usbDevice->busWrite(REG_ER0, 0x82); // mat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x08);
  m_usbDevice->busWrite(REG_ER0, 0x87); // ror
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x00);
  m_usbDevice->busWrite(REG_ER0, 0x84); // dor
  waitNotBusy();

  // Draw a header in the service row.
  m_usbDevice->busWrite(REG_R0, 0x01); // krf with auto-increment
  m_usbDevice->busWrite(REG_R2, 0x01); // B
  m_usbDevice->busWrite(REG_R3, 0x52); // A
  m_usbDevice->busWrite(REG_R6, 0);
  m_usbDevice->busWrite(REG_R7, 0);
  for (uint8_t x = 0; x < 40; ++x) {
    m_usbDevice->busWrite(REG_ER1, '0' + (x % 10)); // C
    waitNotBusy();
  }

  // Clear the rest of the screen with a pattern, numbering the rows with the
  // leftmost character.
  for (uint8_t y = 8, real_y = 1; y < 8 + 24; ++y) {
    m_usbDevice->busWrite(REG_R6, y);
    m_usbDevice->busWrite(REG_R7, 0);

    // First column.
    m_usbDevice->busWrite(REG_R2, 0x01);                   // B
    m_usbDevice->busWrite(REG_R3, 0x52);                   // A
    m_usbDevice->busWrite(REG_ER1, '0' + (real_y++ % 10)); // C
    waitNotBusy();

    // Rest of the columns.
    m_usbDevice->busWrite(REG_R2, 0x20); // B
    m_usbDevice->busWrite(REG_R3, 0x34); // A
    for (uint8_t x = 1; x < 40; ++x) {
      m_usbDevice->busWrite(REG_ER1, 0x3f); // C
      waitNotBusy();
    }
  }

  // Draw main text in double width and double height.
  const char *text = "Hello 40 columns!";
  m_usbDevice->busWrite(REG_R2, 0x0b); // B
  m_usbDevice->busWrite(REG_R3, 0x69); // A
  for (uint8_t i = 0; i < strlen(text); ++i) {
    m_usbDevice->busWrite(REG_R6, 18);        // y
    m_usbDevice->busWrite(REG_R7, 3 + 2 * i); // x

    m_usbDevice->busWrite(REG_ER1, text[i]); // C
    waitNotBusy();
    m_usbDevice->busWrite(REG_ER1, text[i]); // C
    waitNotBusy();

    m_usbDevice->busWrite(REG_R6, 19);        // y
    m_usbDevice->busWrite(REG_R7, 3 + 2 * i); // x

    m_usbDevice->busWrite(REG_ER1, text[i]); // C
    waitNotBusy();
    m_usbDevice->busWrite(REG_ER1, text[i]); // C
    waitNotBusy();
  }
}

void MainWindow::execPresetHelloWorld80() {
  m_usbDevice->busWrite(REG_ER0, 0x91); // nop
  waitNotBusy();

  if (m_usbDevice->videoChipType() == VideoChipType::EF9345) {
    m_usbDevice->busWrite(REG_R1, 0xd0);
  } else {
    m_usbDevice->busWrite(REG_R1, 0xc0);
  }
  m_usbDevice->busWrite(REG_ER0, 0x81); // tgs
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x67);
  m_usbDevice->busWrite(REG_ER0, 0x83); // pat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x00);
  m_usbDevice->busWrite(REG_ER0, 0x82); // mat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x08);
  m_usbDevice->busWrite(REG_ER0, 0x87); // ror
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x39);
  m_usbDevice->busWrite(REG_ER0, 0x84); // dor
  waitNotBusy();

  // Draw a header in the service row.
  m_usbDevice->busWrite(REG_R0, 0x51); // krl with auto-increment
  m_usbDevice->busWrite(REG_R3, 0x00); // A
  m_usbDevice->busWrite(REG_R6, 0);
  m_usbDevice->busWrite(REG_R7, 0);
  for (uint8_t x = 0; x < 80; ++x) {
    m_usbDevice->busWrite(REG_ER1, '0' + (x % 10)); // C
    waitNotBusy();
  }

  // Clear the rest of the screen with a pattern, numbering the rows with the
  // leftmost character.
  for (uint8_t y = 8, real_y = 1; y < 8 + 24; ++y) {
    m_usbDevice->busWrite(REG_R6, y);
    m_usbDevice->busWrite(REG_R7, 0);

    // First column.
    m_usbDevice->busWrite(REG_R3, 0x00);                   // A
    m_usbDevice->busWrite(REG_ER1, '0' + (real_y++ % 10)); // C
    waitNotBusy();

    // Rest of the columns.
    if (m_usbDevice->videoChipType() == VideoChipType::EF9345) {
      // A chessboard-like pattern made of mosaic characters.
      m_usbDevice->busWrite(REG_R3, y % 2 ? 0x99 : 0x77); // A
      for (uint8_t x = 1; x < 80; ++x) {
        m_usbDevice->busWrite(REG_ER1, y % 2 ? 0xe6 : 0x99); // C
        waitNotBusy();
      }
    } else {
      // A grid separated by '+' extended characters.
      m_usbDevice->busWrite(REG_R3, 0x99); // A
      for (uint8_t x = 1; x < 80; ++x) {
        m_usbDevice->busWrite(REG_ER1, 0x85); // C
        waitNotBusy();
      }
    }
  }

  // Draw main text.
  const char *text = "Hello 80 columns!";
  m_usbDevice->busWrite(REG_R3, 0xcc); // A
  m_usbDevice->busWrite(REG_R6, 19);   // y
  m_usbDevice->busWrite(REG_R7, 16);   // x
  for (uint8_t i = 0; i < strlen(text); ++i) {
    m_usbDevice->busWrite(REG_ER1, text[i]); // C
    waitNotBusy();
  }
}

void MainWindow::execPresetUniformColor() {
  QStringList options = {
      // In order of increasing grayscale-equivalent brightness.
      "Black", "Blue", "Red", "Magenta", "Green", "Cyan", "Yellow", "White",
  };
  bool ok;
  QString choice = QInputDialog::getItem(
      this, "Set uniform color",
      "This preset sets the margin color and then disables the bulk, so that\n"
      "it works even if no video RAM is present. What color should be set?",
      options, 0, false, &ok);
  int color = options.indexOf(choice);
  if (color == -1 || !ok) {
    return; // canceled
  }

  color = ((color >> 1) & 3) | ((color & 1) << 2);

  m_usbDevice->busWrite(REG_ER0, 0x91); // nop
  waitNotBusy();

  if (m_usbDevice->videoChipType() == VideoChipType::EF9345) {
    m_usbDevice->busWrite(REG_R1, 0x10);
  } else {
    m_usbDevice->busWrite(REG_R1, 0x00);
  }
  m_usbDevice->busWrite(REG_ER0, 0x81); // tgs
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x30);
  m_usbDevice->busWrite(REG_ER0, 0x83); // pat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x08 | color);
  m_usbDevice->busWrite(REG_ER0, 0x82); // mat
  waitNotBusy();
}

void MainWindow::execPresetColorBands() {
  m_usbDevice->busWrite(REG_ER0, 0x91); // nop
  waitNotBusy();

  if (m_usbDevice->videoChipType() == VideoChipType::EF9345) {
    m_usbDevice->busWrite(REG_R1, 0x10);
  } else {
    m_usbDevice->busWrite(REG_R1, 0x00);
  }
  m_usbDevice->busWrite(REG_ER0, 0x81); // tgs
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x67);
  m_usbDevice->busWrite(REG_ER0, 0x83); // pat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x00);
  m_usbDevice->busWrite(REG_ER0, 0x82); // mat
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x08);
  m_usbDevice->busWrite(REG_ER0, 0x87); // ror
  waitNotBusy();
  m_usbDevice->busWrite(REG_R1, 0x00);
  m_usbDevice->busWrite(REG_ER0, 0x84); // dor
  waitNotBusy();

  // Clear the whole screen.
  m_usbDevice->busWrite(REG_R0, 0x01); // krf with auto-increment
  m_usbDevice->busWrite(REG_R2, 0x00); // B
  m_usbDevice->busWrite(REG_R3, 0x00); // A
  auto clearLine = [&](uint8_t y) {
    m_usbDevice->busWrite(REG_R6, y);
    m_usbDevice->busWrite(REG_R7, 0); // x
    for (uint8_t x = 0; x < 40; ++x) {
      m_usbDevice->busWrite(REG_ER1, ' '); // C
      waitNotBusy();
    }
  };
  clearLine(0);
  for (uint8_t y = 8; y < 8 + 24; y++) {
    clearLine(y);
  }

  // Draw a band in double width and double height.
  auto drawBand = [&](uint8_t y, uint8_t a, const char *text) {
    m_usbDevice->busWrite(REG_R2, 0x0b); // B
    m_usbDevice->busWrite(REG_R3, a);    // A
    m_usbDevice->busWrite(REG_R6, y);    // y
    m_usbDevice->busWrite(REG_R7, 0);    // x
    for (uint8_t i = 0; i < 20; ++i) {
      m_usbDevice->busWrite(REG_ER1, text[i]); // C
      waitNotBusy();
      m_usbDevice->busWrite(REG_ER1, text[i]); // C
      waitNotBusy();
    }
    m_usbDevice->busWrite(REG_R6, y + 1); // y
    m_usbDevice->busWrite(REG_R7, 0);     // x
    for (uint8_t i = 0; i < 20; ++i) {
      m_usbDevice->busWrite(REG_ER1, text[i]); // C
      waitNotBusy();
      m_usbDevice->busWrite(REG_ER1, text[i]); // C
      waitNotBusy();
    }
  };

  drawBand(0x09, 0x70, "              B G R ");
  drawBand(0x0C, 0x70, " #0 Black     0 0 0 ");
  drawBand(0x0E, 0x74, " #4 Blue      1 0 0 ");
  drawBand(0x10, 0x71, " #1 Red       0 0 1 ");
  drawBand(0x12, 0x75, " #5 Magenta   1 0 1 ");
  drawBand(0x14, 0x02, " #2 Green     0 1 0 ");
  drawBand(0x16, 0x06, " #6 Cyan      1 1 0 ");
  drawBand(0x18, 0x03, " #3 Yellow    0 1 1 ");
  drawBand(0x1A, 0x07, " #7 White     1 1 1 ");
}
