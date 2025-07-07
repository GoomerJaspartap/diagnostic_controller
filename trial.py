import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QLineEdit, QPushButton, QHBoxLayout, QFormLayout, QGroupBox, QSpacerItem, QSizePolicy)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

class ValueTrackerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Value Tracker with Threshold")
        self.setMinimumSize(800, 600)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        self.init_form()
        self.init_plot()

        self.points = []

        self.setLayout(self.layout)

    def init_form(self):
        form_group = QGroupBox("Configuration")
        form_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        font = QFont("Arial", 10)

        self.start_time_input = QLineEdit("0"); self.start_time_input.setFont(font)
        self.time_to_achieve_input = QLineEdit("10"); self.time_to_achieve_input.setFont(font)
        self.threshold_input = QLineEdit("5"); self.threshold_input.setFont(font)
        self.start_value_input = QLineEdit("0"); self.start_value_input.setFont(font)
        self.target_value_input = QLineEdit("100"); self.target_value_input.setFont(font)
        self.current_time_input = QLineEdit(); self.current_time_input.setFont(font)
        self.current_value_input = QLineEdit(); self.current_value_input.setFont(font)

        form_layout.addRow("Start Time:", self.start_time_input)
        form_layout.addRow("Time to Achieve:", self.time_to_achieve_input)
        form_layout.addRow("Threshold:", self.threshold_input)
        form_layout.addRow("Start Value:", self.start_value_input)
        form_layout.addRow("Target Value:", self.target_value_input)
        form_layout.addRow("Current Time:", self.current_time_input)
        form_layout.addRow("Current Value:", self.current_value_input)

        # Buttons
        self.add_button = QPushButton("Add Point")
        self.add_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.add_button.setStyleSheet("QPushButton { padding: 8px; background-color: #007ACC; color: white; border-radius: 5px; } QPushButton:hover { background-color: #005F9E; }")
        self.add_button.clicked.connect(self.add_point)

        self.clear_button = QPushButton("Clear Points")
        self.clear_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.clear_button.setStyleSheet("QPushButton { padding: 8px; background-color: #d9534f; color: white; border-radius: 5px; } QPushButton:hover { background-color: #c9302c; }")
        self.clear_button.clicked.connect(self.clear_points)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.clear_button)
        form_layout.addRow(button_layout)

        form_group.setLayout(form_layout)
        self.layout.addWidget(form_group)


    def init_plot(self):
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

    def compute_expected(self, start_time, time_to_achieve, current_time, start_value, target_value):
        m = (target_value - start_value) / time_to_achieve
        b = start_value - m * start_time

        if current_time < start_time:
            expected_value = start_value
        elif current_time >= start_time + time_to_achieve:
            expected_value = target_value
        else:
            expected_value = m * current_time + b

        return np.clip(expected_value, start_value, target_value)
    
    def add_point(self):
        try:
            start_time = float(self.start_time_input.text())
            time_to_achieve = float(self.time_to_achieve_input.text())
            threshold = float(self.threshold_input.text())
            start_value = float(self.start_value_input.text())
            target_value = float(self.target_value_input.text())
            current_time = float(self.current_time_input.text())
            current_value = float(self.current_value_input.text())

            expected_value = self.compute_expected(start_time, time_to_achieve, current_time, start_value, target_value)
            in_bounds = abs(current_value - expected_value) <= threshold and current_value <= target_value

            self.points.append((current_time, current_value, in_bounds))
            self.update_plot(start_time, time_to_achieve, threshold, start_value, target_value)

            self.current_time_input.clear()
            self.current_value_input.clear()
        except ValueError:
            pass

    def update_plot(self, start_time, time_to_achieve, threshold, start_value, target_value):
        self.ax.clear()
        self.ax.set_facecolor('#f8f8f8')

        m = (target_value - start_value) / time_to_achieve
        b = start_value - m * start_time
        times = np.linspace(start_time - 1, start_time + time_to_achieve + 1, 200)
        expected_values = np.clip(m * times + b, start_value, target_value)
        upper = np.clip(expected_values + threshold, start_value, target_value)
        lower = np.clip(expected_values - threshold, start_value, target_value)

        self.ax.plot(times, expected_values, label="Expected Curve", linewidth=2, color='blue')
        self.ax.plot(times, upper, '--', color='orange', label="Upper Threshold")
        self.ax.plot(times, lower, '--', color='orange', label="Lower Threshold")

        for t, v, valid in self.points:
            color = 'green' if valid else 'red'
            self.ax.scatter(t, v, color=color, edgecolors='black', zorder=5)
            self.ax.annotate(f"({t:.2f}, {v:.2f})", (t, v), textcoords="offset points", xytext=(5, 5), ha='left', fontsize=8)

        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Value")
        self.ax.legend()
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.canvas.draw()
    def clear_points(self):
        self.points.clear()
        try:
            start_time = float(self.start_time_input.text())
            time_to_achieve = float(self.time_to_achieve_input.text())
            threshold = float(self.threshold_input.text())
            start_value = float(self.start_value_input.text())
            target_value = float(self.target_value_input.text())
            self.update_plot(start_time, time_to_achieve, threshold, start_value, target_value)
        except ValueError:
            self.ax.clear()
            self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ValueTrackerGUI()
    window.show()
    sys.exit(app.exec_())
