import os

from ..Qt import QtCore, QtGui, QtWidgets, Worker

os.environ['OPENCV_LOG_LEVEL'] = 'OFF'
try:
    import cv2  # noqa: E402
except ImportError:
    cv2 = None


class CameraWidget(QtWidgets.QWidget):
    """Widget to select and display video feed from connected cameras.
    """
    # Signal to receive cameras found by the worker
    cameras_found = QtCore.Signal(list)
    scan_completed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize UI components
        self.camera_selector = QtWidgets.QComboBox(self)
        self.refresh_button = QtWidgets.QPushButton("Refresh Cameras", self)
        self.video_label = QtWidgets.QLabel("No camera selected.", self)
        self.video_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Layout setup
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.camera_selector)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

        # Initialize camera variables
        self.cameras = []
        self.current_camera_index = None
        self.cap = None

        # If OpenCV is not available, display a message
        if cv2 is None:
            self.video_label.setText("OpenCV not found. Camera feed unavailable.")
            return

        # Initialize timer for frame capture
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Connect signals
        self.camera_selector.currentIndexChanged.connect(self.select_camera)
        self.refresh_button.clicked.connect(self.refresh_cameras)

        # Start scanning cameras
        self.scan_cameras_async()

    def scan_cameras_async(self):
        """Start scanning for available cameras asynchronously."""
        self.camera_selector.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.video_label.setText("Scanning for cameras...")

        # Initialize Worker for camera scanning
        self.scan_thread = QtCore.QThread()
        self.scan_worker = Worker(self.scan_cameras, self.scan_thread)
        self.scan_worker.finished.connect(self.handle_scan_results)
        self.scan_thread.start()

    def scan_cameras(self):
        """Scan for available cameras."""
        found_cameras = []
        index = 0
        while True:
            cap = cv2.VideoCapture(index)
            if not cap.read()[0]:
                break

            if cap.isOpened():
                found_cameras.append(index)
                cap.release()
            index += 1

        return found_cameras

    def handle_scan_results(self, found_cameras):
        """Handle the results from the camera scan."""
        self.cameras = found_cameras
        self.camera_selector.clear()

        if self.cameras:
            for index in self.cameras:
                self.camera_selector.addItem(f"Camera {index}", index)
            self.camera_selector.setCurrentIndex(0)
            self.select_camera(0)
        else:
            self.video_label.setText("No cameras found.")

        self.camera_selector.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def refresh_cameras(self):
        """Refresh the list of available cameras."""
        if self.cap:
            self.cap.release()
            self.cap = None
            self.timer.stop()
            self.video_label.setText("No camera selected.")

        self.scan_cameras_async()

    def select_camera(self, index):
        """Select and start the chosen camera."""
        if self.cap:
            self.cap.release()
            self.cap = None
            self.timer.stop()

        if index < 0 or index >= len(self.cameras):
            self.video_label.setText("Invalid camera selected.")
            return

        camera_index = self.cameras[index]
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to open Camera {camera_index}")
            self.video_label.setText(f"Failed to open Camera {camera_index}")
            return

        self.current_camera_index = camera_index
        self.video_label.setText(f"Starting Camera {camera_index}...")

        self.timer.start(30)  # Approximately 30 FPS

    def update_frame(self):
        """Capture frame from camera and display it."""
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if ret:
            # Convert the image to RGB format
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_image.shape
            bytes_per_line = 3 * width
            qt_image = QtGui.QImage(
                rgb_image.data, width, height, bytes_per_line, QtGui.QImage.Format.Format_RGB888
            )
            pixmap = QtGui.QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(
                pixmap.scaled(
                    self.video_label.size(),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.video_label.setText("Failed to read frame.")

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Handle the widget closing event to release resources."""
        if self.cap:
            self.cap.release()
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        event.accept()
