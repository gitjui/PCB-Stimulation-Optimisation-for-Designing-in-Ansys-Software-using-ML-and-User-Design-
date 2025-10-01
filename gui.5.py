import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class OptimizationUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCB Coil Optimization")
        self.setStyleSheet("background-color: #121212; color: white; font-size: 14px;")
        layout = QVBoxLayout()

        self.dict_data = None
        self.optimal_result = None

        # Graph selection
        layout.addWidget(QLabel("Select Graphs (Ctrl+Click to select multiple):"))
        self.graph_list = QListWidget()
        for graph in [
            "Quality Factor vs Number of Turns",
            "SRF vs Coil Radius",
            "Q Factor vs Air Gap",
            "Optimal Point Comparison"
        ]:
            self.graph_list.addItem(QListWidgetItem(graph))
        self.graph_list.setSelectionMode(QListWidget.MultiSelection)
        self.graph_list.setStyleSheet("background-color: #1e1e1e; padding: 8px;")
        layout.addWidget(self.graph_list)

        # Load Data button
        self.load_button = QPushButton("Load Data Files")
        self.load_button.setStyleSheet("background-color: #34a853; padding: 10px; border-radius: 5px;")
        self.load_button.clicked.connect(self.load_data)
        layout.addWidget(self.load_button)

        # Plot button
        self.plot_button = QPushButton("Plot Selected Graphs")
        self.plot_button.setStyleSheet("background-color: #1a73e8; padding: 10px;")
        self.plot_button.clicked.connect(self.plot_graphs)
        layout.addWidget(self.plot_button)

        # Matplotlib figure
        self.figure, _ = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def load_data(self):
        dict_path, _ = QFileDialog.getOpenFileName(self, "Open Dict Search Results", "", "CSV Files (*.csv)")
        json_path, _ = QFileDialog.getOpenFileName(self, "Open Optimal Results", "", "JSON Files (*.json)")

        if not dict_path or not json_path:
            QMessageBox.warning(self, "Warning", "Please select both files")
            return

        try:
            # Load CSV with auto delimiter detection
            self.dict_data = pd.read_csv(dict_path, sep=None, engine='python')
            self.dict_data.columns = self.dict_data.columns.str.strip()

            # If it read one column, attempt manual cleanup
            if len(self.dict_data.columns) == 1 and ',' in self.dict_data.columns[0]:
                self.dict_data = self.dict_data[self.dict_data.columns[0]].str.split(',', expand=True)
                self.dict_data.columns = self.dict_data.iloc[0]
                self.dict_data = self.dict_data.drop(index=0).reset_index(drop=True)
                self.dict_data.columns = self.dict_data.columns.str.strip()
                self.dict_data = self.dict_data.apply(pd.to_numeric, errors='ignore')

            print("Cleaned CSV Columns:", self.dict_data.columns.tolist())

            # Load optimal result from JSON with  'obj'
            with open(json_path) as f:
                all_results = json.load(f)
            best_idx = max(all_results, key=lambda k: all_results[k]['obj'])
            self.optimal_result = all_results[best_idx]['all']

            QMessageBox.information(self, "Success", "Data loaded and processed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def plot_graphs(self):
        if self.dict_data is None or self.optimal_result is None:
            QMessageBox.warning(self, "Warning", "Please load data files first!")
            return

        selected_items = self.graph_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select at least one graph to plot!")
            return

        graph_titles = [item.text() for item in selected_items]
        num_graphs = len(graph_titles)
        self.figure.clf()

        for i, title in enumerate(graph_titles):
            ax = self.figure.add_subplot(num_graphs, 1, i + 1)
            ax.grid(color='#404040')
            ax.set_facecolor('#121212')
            self.figure.set_facecolor('#121212')
            ax.tick_params(colors='white')

            if title == "Quality Factor vs Number of Turns":
                if 'n' in self.dict_data.columns and 'Q' in self.dict_data.columns:
                    # Sort data by 'n' for line plot
                    sorted_data = self.dict_data.sort_values(by='n')
                    ax.plot(sorted_data['n'], sorted_data['Q'], 'bo-', label='Search Results')
                    if 'n' in self.optimal_result and 'Q' in self.optimal_result:
                        ax.plot(self.optimal_result['n'], self.optimal_result['Q'], 'ro', markersize=10, label='Optimal')
                    ax.set_xlabel("Number of Turns", color='white')
                    ax.set_ylabel("Quality Factor (Q)", color='white')
                else:
                    ax.text(0.5, 0.5, "Missing 'n' or 'Q' columns", ha='center', color='white')

            elif title == "SRF vs Coil Radius":
                if 'rout' in self.dict_data.columns and 'SRF1' in self.dict_data.columns:
                    # Sort data by 'rout' for line plot
                    sorted_data = self.dict_data.sort_values(by='rout')
                    ax.plot(sorted_data['rout'], sorted_data['SRF1'], 'co-', label='Search Results')
                    if 'rout' in self.optimal_result and 'SRF1' in self.optimal_result:
                        ax.plot(self.optimal_result['rout'], self.optimal_result['SRF1'], 'mo', markersize=10, label='Optimal')
                    ax.set_xlabel("Coil Radius (mm)", color='white')
                    ax.set_ylabel("SRF1 (MHz)", color='white')
                else:
                    ax.text(0.5, 0.5, "Missing 'rout' or 'SRF1' columns", ha='center', color='white')

            elif title == "Q Factor vs Air Gap":
                if 'space' in self.dict_data.columns and 'Q' in self.dict_data.columns:
                    # Sort data by 'space' for line plot
                    sorted_data = self.dict_data.sort_values(by='space')
                    ax.plot(sorted_data['space'], sorted_data['Q'], 'go-', label='Search Results')
                    if 'space' in self.optimal_result and 'Q' in self.optimal_result:
                        ax.plot(self.optimal_result['space'], self.optimal_result['Q'], 'ro', markersize=10, label='Optimal')
                    ax.set_xlabel("Air Gap (mm)", color='white')
                    ax.set_ylabel("Quality Factor (Q)", color='white')
                else:
                    ax.text(0.5, 0.5, "Missing 'space' or 'Q' columns", ha='center', color='white')

            elif title == "Optimal Point Comparison":
                labels = []
                search_vals = []
                optimal_vals = []

                if 'SRF1' in self.dict_data.columns and 'SRF1' in self.optimal_result:
                    labels.append('SRF1')
                    search_vals.append(self.dict_data['SRF1'].astype(float).mean())
                    optimal_vals.append(self.optimal_result['SRF1'])

                if 'Q' in self.dict_data.columns and 'Q' in self.optimal_result:
                    labels.append('Q')
                    search_vals.append(self.dict_data['Q'].astype(float).mean())
                    optimal_vals.append(self.optimal_result['Q'])

                if labels:
                    x = range(len(labels))
                    ax.bar(x, search_vals, width=0.4, label='Average Search')
                    ax.bar([i + 0.4 for i in x], optimal_vals, width=0.4, label='Optimal Result')
                    ax.set_xticks([i + 0.2 for i in x])
                    ax.set_xticklabels(labels)
                    ax.set_ylabel("Value", color='white')
                else:
                    ax.text(0.5, 0.5, "No matching metrics found", ha='center', color='white')

            ax.set_title(title, color='white', fontsize=10)
            ax.legend(facecolor='#1e1e1e', edgecolor='none', labelcolor='white')

        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OptimizationUI()
    window.show()
    sys.exit(app.exec_())
