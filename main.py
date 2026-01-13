# Made by Cocorino with Love

import sys
import time
import subprocess
import platform
from datetime import datetime
import psutil
import pyqtgraph as pg

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer


class MonitorWorker(QThread):
    data = pyqtSignal(float, float, float, bool, str)

    def __init__(self):
        super().__init__()
        self.running = True

    def ping(self):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            out = subprocess.check_output(
                ["ping", param, "1", "8.8.8.8"],
                stderr=subprocess.DEVNULL
            ).decode().lower()

            if "time=" in out:
                return float(out.split("time=")[-1].split()[0]), False
        except:
            pass
        return 0.0, True

    def run(self):
        last = psutil.net_io_counters()

        while self.running:
            time.sleep(1)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            current = psutil.net_io_counters()
            down = (current.bytes_recv - last.bytes_recv) * 8 / 1_000_000
            up = (current.bytes_sent - last.bytes_sent) * 8 / 1_000_000
            last = current

            ping, lost = self.ping()
            self.data.emit(down, up, ping, lost, now)



class InternetMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Internet Speed Monitor (GPU)")
        self.resize(1100, 700)
        self.x = []
        self.down = []
        self.up = []
        self.ping = []
        self.loss = []
        self.timestamps = []
        self.counter = 0
        self.total_loss = 0
        self.init_ui()
        self.init_graphs()
        self.init_timer()
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        self.alert = QSpinBox()
        self.alert.setRange(1, 10_000)
        self.alert.setValue(50)

        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.start)

        top.addWidget(QLabel("Alert ↓ below (Mbps):"))
        top.addWidget(self.alert)
        top.addStretch()
        top.addWidget(self.start_btn)

        layout.addLayout(top)

        self.status = QLabel("Status: Idle")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.graphs = QVBoxLayout()
        layout.addLayout(self.graphs)


    def init_graphs(self):
        pg.setConfigOptions(antialias=True)

        self.speed_plot = pg.PlotWidget(title="Internet Speed (Mbps)")
        self.speed_plot.setLabel("left", "Mbps")
        self.speed_plot.setLabel("bottom", "Time (samples)")
        self.speed_plot.showGrid(x=True, y=True)

        self.speed_down = self.speed_plot.plot(pen=pg.mkPen("#00A2FF", width=2), name="Download")
        self.speed_up = self.speed_plot.plot(pen=pg.mkPen("#FF8C00", width=2), name="Upload")

        self.ping_plot = pg.PlotWidget(title="Ping & Packet Loss")
        self.ping_plot.setLabel("left", "ms / %")
        self.ping_plot.setLabel("bottom", "Time (samples)")
        self.ping_plot.showGrid(x=True, y=True)

        self.ping_line = self.ping_plot.plot(pen=pg.mkPen("#00FF7F", width=2), name="Ping")
        self.loss_line = self.ping_plot.plot(pen=pg.mkPen("#FF4040", width=2), name="Loss")

        self.graphs.addWidget(self.speed_plot)
        self.graphs.addWidget(self.ping_plot)

    def init_timer(self):
        self.timer = QTimer()
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.redraw)

    def update(self, down, up, ping, lost, timestamp):
        self.counter += 1
        self.x.append(self.counter)
        self.down.append(down)
        self.up.append(up)
        self.ping.append(ping)
        self.timestamps.append(timestamp)

        if lost:
            self.total_loss += 1
        self.loss.append((self.total_loss / self.counter) * 100)

        msg = (
            f"[{timestamp}]  "
            f"↓ {down:.2f} Mbps | ↑ {up:.2f} Mbps | Ping {ping:.1f} ms"
        )

        if down < self.alert.value():
            msg += "  ⚠ SPEED DROP"

        self.status.setText(msg)

    def redraw(self):
        if not self.x:
            return

        self.speed_down.setData(self.x, self.down)
        self.speed_up.setData(self.x, self.up)

        self.ping_line.setData(self.x, self.ping)
        self.loss_line.setData(self.x, self.loss)

    def start(self):
        self.x.clear()
        self.down.clear()
        self.up.clear()
        self.ping.clear()
        self.loss.clear()
        self.timestamps.clear()
        self.counter = 0
        self.total_loss = 0

        self.worker = MonitorWorker()
        self.worker.data.connect(self.update)
        self.worker.start()

        self.timer.start()

    def closeEvent(self, event):
        if hasattr(self, "worker"):
            self.worker.running = False
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: #e6e6e6;
            font-family: Segoe UI;
            font-size: 10pt;
        }
        QPushButton {
            background-color: #0078D4;
            border-radius: 6px;
            padding: 6px 14px;
        }
        QPushButton:hover {
            background-color: #106EBE;
        }
    """)

    win = InternetMonitor()
    win.show()
    sys.exit(app.exec())
