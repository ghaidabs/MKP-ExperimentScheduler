import pandas as pd
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtGui import QFont, QPalette, QColor, QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, List, Tuple, Optional

from data import load_dataset, save_dataset, DEFAULT_THRESHOLDS, REQUIRED_COLUMNS, next_enumber_id
from solver import build_and_solve_gurobi


class PandasModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df.copy()

    def update(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._df.index)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iloc[index.row(), index.column()]
        if role == Qt.DisplayRole:
            return str(value)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(self._df.index[section])




class AddExperimentDialog(QDialog):
    def __init__(self, existing_experiments: List[Tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add New Experiment')
        self.setMinimumWidth(480)

        self.setFont(QFont('Segoe UI', 10))

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.value_spin = QDoubleSpinBox(); self.value_spin.setRange(0, 1e9); self.value_spin.setDecimals(2)
        self.lab_hours_spin = QDoubleSpinBox(); self.lab_hours_spin.setRange(0, 1e6); self.lab_hours_spin.setDecimals(2)
        self.human_hours_spin = QDoubleSpinBox(); self.human_hours_spin.setRange(0, 1e6); self.human_hours_spin.setDecimals(2)
        self.cost_spin = QDoubleSpinBox(); self.cost_spin.setRange(0, 1e9); self.cost_spin.setDecimals(2)
        self.reagentA_spin = QDoubleSpinBox(); self.reagentA_spin.setRange(0, 1e9); self.reagentA_spin.setDecimals(2)
        self.reagentB_spin = QDoubleSpinBox(); self.reagentB_spin.setRange(0, 1e9); self.reagentB_spin.setDecimals(2)
        self.reagentC_spin = QDoubleSpinBox(); self.reagentC_spin.setRange(0, 1e9); self.reagentC_spin.setDecimals(2)
        self.hplc_spin = QSpinBox(); self.hplc_spin.setRange(0, 100)
        self.gc_spin = QSpinBox(); self.gc_spin.setRange(0, 100)
        self.mic_spin = QSpinBox(); self.mic_spin.setRange(0, 100)
        self.ms_spin = QSpinBox(); self.ms_spin.setRange(0, 100)
        self.safety_spin = QSpinBox(); self.safety_spin.setRange(1, 5)

        self.deps_list = QListWidget()
        self.deps_list.setSelectionMode(QListWidget.MultiSelection)
        self.deps_list.setMaximumHeight(150)
        if existing_experiments:
            for eid, name in existing_experiments:
                it = QListWidgetItem(name)
                it.setData(Qt.UserRole, eid)
                self.deps_list.addItem(it)
        else:
            it = QListWidgetItem('(no existing experiments)')
            it.setFlags(Qt.NoItemFlags)
            self.deps_list.addItem(it)

        form.addRow('Name', self.name_edit)
        form.addRow('Value (priority/benefit)', self.value_spin)
        form.addRow('Lab hours', self.lab_hours_spin)
        form.addRow('Human hours', self.human_hours_spin)
        form.addRow('Cost (USD)', self.cost_spin)
        form.addRow('Reagent A (mL)', self.reagentA_spin)
        form.addRow('Reagent B (g)', self.reagentB_spin)
        form.addRow('Reagent C (mmol)', self.reagentC_spin)
        form.addRow('HPLC', self.hplc_spin)
        form.addRow('GC', self.gc_spin)
        form.addRow('Microscope', self.mic_spin)
        form.addRow('MassSpec', self.ms_spin)
        form.addRow('Safety level', self.safety_spin)
        form.addRow(QLabel('Dependencies on other experiments'), self.deps_list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.on_accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout()
        lay.addLayout(form)
        lay.addWidget(btns)
        self.setLayout(lay)

    def on_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, 'Validation', 'Name is required.')
            return
        if self.value_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation', 'Value must be > 0.')
            return
        if self.lab_hours_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation', 'Lab hours must be > 0.')
            return
        if self.human_hours_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation', 'Human hours must be > 0.')
            return
        if self.cost_spin.value() <= 0:
            QMessageBox.warning(self, 'Validation', 'Cost must be > 0.')
            return
        self.accept()

    def get_data(self) -> Dict:
        deps = []
        for it in self.deps_list.selectedItems():
            stored_id = it.data(Qt.UserRole)
            if stored_id:
                deps.append(str(stored_id))
        deps_str = '[' + ','.join(f'"{d}"' for d in deps) + ']' if deps else ''
        return {
            'name': self.name_edit.text().strip(),
            'value': float(self.value_spin.value()),
            'lab_hours': float(self.lab_hours_spin.value()),
            'human_hours': float(self.human_hours_spin.value()),
            'cost_usd': float(self.cost_spin.value()),
            'reagent_A_ml': float(self.reagentA_spin.value()),
            'reagent_B_g': float(self.reagentB_spin.value()),
            'reagent_C_mmol': float(self.reagentC_spin.value()),
            'instr_HPLC': int(self.hplc_spin.value()),
            'instr_GC': int(self.gc_spin.value()),
            'instr_Microscope': int(self.mic_spin.value()),
            'instr_MassSpec': int(self.ms_spin.value()),
            'safety_level': int(self.safety_spin.value()),
            'dependencies': deps_str,
        }


class VisualizationWindow(QWidget):
    def __init__(self, parent_main: 'MainWindow'):
        super().__init__()
        self.setWindowTitle('Visualizations')
        self.resize(900, 700)
        self.parent_main = parent_main

        tabs = QTabWidget()
        tabs.addTab(self._resource_tab(), 'Resource Utilization')
        tabs.addTab(self._safety_tab(), 'Safety Distribution')

        lay = QVBoxLayout()
        lay.addWidget(tabs)
        self.setLayout(lay)

    def _make_canvas(self):
        fig = Figure(figsize=(6, 4))
        fig.patch.set_facecolor('white')
        canvas = FigureCanvas(fig)
        return fig, canvas

    def _resource_tab(self):
        fig, canvas = self._make_canvas()
        ax = fig.add_subplot(111)

        df = self.parent_main.df
        sel = self.parent_main.last_results_df
        thr = DEFAULT_THRESHOLDS

        resources = [
            ('Lab hours / week', 'lab_hours', 'total_lab_hours_per_week'),
            ('Human hours / week', 'human_hours', 'human_hours_available'),
            ('Budget (USD)', 'cost_usd', 'total_budget_usd'),
            ('Reagent A (mL)', 'reagent_A_ml', 'reagent_A_ml_available'),
            ('Reagent B (g)', 'reagent_B_g', 'reagent_B_g_available'),
            ('Reagent C (mmol)', 'reagent_C_mmol', 'reagent_C_mmol_available'),
        ]

        labels = []
        used_vals = []
        avail_vals = []

        for label, col, thr_key in resources:
            labels.append(label)

            used = sel[col].sum() if not sel.empty else 0
            avail = thr.get(thr_key, 0)

            used_vals.append(used)
            avail_vals.append(avail)

        y = np.arange(len(labels))

        ax.barh(y - 0.15, used_vals, height=0.3, label='Used', color='#FF8C00')
        ax.barh(y + 0.15, avail_vals, height=0.3, label='Available', color='#2E8B57' )

        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_title('Resource Utilization (Used vs Available)')
        ax.legend()
        fig.tight_layout()

        w = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(canvas)
        w.setLayout(layout)
        return w

        

    def _safety_tab(self):
        fig, canvas = self._make_canvas()
        ax = fig.add_subplot(111)

        df = self.parent_main.df
        sel = self.parent_main.last_results_df if not self.parent_main.last_results_df.empty else pd.DataFrame()

        full_counts = df['safety_level'].value_counts().sort_index()
        selected_counts = sel['safety_level'].value_counts().sort_index() if not sel.empty else pd.Series(dtype=int)

        levels = sorted(set(full_counts.index.tolist() + selected_counts.index.tolist()))
        counts_full = [full_counts.get(l, 0) for l in levels]
        counts_sel = [selected_counts.get(l, 0) for l in levels]

        x = np.arange(len(levels))
        ax.bar(x - 0.2, counts_full, width=0.4, label='All experiments', color='#2E8B57')
        ax.bar(x + 0.2, counts_sel, width=0.4, label='Selected', color='#FF8C00')
        ax.set_xticks(x)
        ax.set_xticklabels([str(l) for l in levels])
        ax.set_xlabel('Safety level')
        ax.set_ylabel('Count')
        ax.set_title('Safety-level distribution (all vs selected)')
        ax.legend()
        fig.tight_layout()

        w = QWidget()
        l = QVBoxLayout()
        l.addWidget(canvas)
        w.setLayout(l)
        return w


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MKP - R&D Experiment Scheduler ')
        self.resize(1200, 750)

        self.setFont(QFont('Segoe UI', 11))

        self.df, self.dataset_path = load_dataset()

        thresholds_group = QFormLayout()

        default_lab_hours = DEFAULT_THRESHOLDS.get('total_lab_hours_per_week', 160.0)
        default_human_hours = DEFAULT_THRESHOLDS.get('human_hours_available', 200.0)
        default_benches = int(default_lab_hours // 40) if default_lab_hours >= 40 else 1
        default_techs = int(default_human_hours // 40) if default_human_hours >= 40 else 1

        self.benches_spin = QSpinBox(); self.benches_spin.setRange(0, 1000); self.benches_spin.setValue(default_benches)
        self.techs_spin = QSpinBox(); self.techs_spin.setRange(0, 1000); self.techs_spin.setValue(default_techs)

        self.budget_spin = QDoubleSpinBox(); self.budget_spin.setRange(0, 1e9); self.budget_spin.setValue(DEFAULT_THRESHOLDS['total_budget_usd'])
        self.reagA_spin = QDoubleSpinBox(); self.reagA_spin.setRange(0, 1e9); self.reagA_spin.setValue(DEFAULT_THRESHOLDS['reagent_A_ml_available'])
        self.reagB_spin = QDoubleSpinBox(); self.reagB_spin.setRange(0, 1e9); self.reagB_spin.setValue(DEFAULT_THRESHOLDS['reagent_B_g_available'])
        self.reagC_spin = QDoubleSpinBox(); self.reagC_spin.setRange(0, 1e9); self.reagC_spin.setValue(DEFAULT_THRESHOLDS['reagent_C_mmol_available'])

        self.hplc_spin = QSpinBox(); self.hplc_spin.setRange(0, 1000); self.hplc_spin.setValue(DEFAULT_THRESHOLDS['instrument_counts']['instr_HPLC'])
        self.gc_spin = QSpinBox(); self.gc_spin.setRange(0, 1000); self.gc_spin.setValue(DEFAULT_THRESHOLDS['instrument_counts']['instr_GC'])
        self.mic_spin = QSpinBox(); self.mic_spin.setRange(0, 1000); self.mic_spin.setValue(DEFAULT_THRESHOLDS['instrument_counts']['instr_Microscope'])
        self.ms_spin = QSpinBox(); self.ms_spin.setRange(0, 1000); self.ms_spin.setValue(DEFAULT_THRESHOLDS['instrument_counts']['instr_MassSpec'])

        thresholds_group.addRow('Number of lab benches', self.benches_spin)
        thresholds_group.addRow('Number of lab techs', self.techs_spin)
        thresholds_group.addRow('Total budget (USD)', self.budget_spin)
        thresholds_group.addRow('Reagent A (mL)', self.reagA_spin)
        thresholds_group.addRow('Reagent B (g)', self.reagB_spin)
        thresholds_group.addRow('Reagent C (mmol)', self.reagC_spin)
        thresholds_group.addRow('Available HPLC', self.hplc_spin)
        thresholds_group.addRow('Available GC', self.gc_spin)
        thresholds_group.addRow('Available Microscope', self.mic_spin)
        thresholds_group.addRow('Available MassSpec', self.ms_spin)

        self.safety_spins = {}
        safety_defaults = DEFAULT_THRESHOLDS.get('safety_limits', {})
        for lvl in range(1, 6):
            sb = QSpinBox()
            sb.setRange(0, 1000)  
            sb.setValue(int(safety_defaults.get(lvl, 0)))
            thresholds_group.addRow(f'Max experiments with safety level {lvl}', sb)
            self.safety_spins[lvl] = sb

        left_box = QGroupBox('Controls and Thresholds')
        left_v = QVBoxLayout()
        left_v.addLayout(thresholds_group)
        left_v.addStretch()

        self.add_btn = QPushButton('Add Experiment')
        self.solve_btn = QPushButton('Solve (Gurobi)')
        self.visualize_btn = QPushButton('Visualize')

        self.add_btn.clicked.connect(self.add_experiment)
        self.solve_btn.clicked.connect(self.solve_model)
        self.visualize_btn.clicked.connect(self.open_visualization_window)

        left_v.addWidget(self.add_btn)
        left_v.addWidget(self.solve_btn)
        left_v.addWidget(self.visualize_btn)       
        left_box.setLayout(left_v)

        header_color = '#2e7d32'
        header_font_size_pt = 13
        left_box.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {header_font_size_pt}pt; color: {header_color}; border: 1px solid #9ccc65; border-radius: 6px; margin-top: 20px; padding: 8px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}")

        self.table = QTableView()
        self.model = PandasModel(self.df)
        self.table.setModel(self.model)
        self.table.setFont(QFont('Segoe UI', 11))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setMinimumSectionSize(90)
        self.table.horizontalHeader().setDefaultSectionSize(120)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(False)
        self.table.setStyleSheet("QTableView { font-size: 11pt; } QHeaderView::section { font-size: 11pt; font-weight: bold; padding: 6px 12px; }")

        self.results_label = QLabel('Scheduled Experiments / Week')
        header_font = QFont('Segoe UI', header_font_size_pt, QFont.Bold)
        self.results_label.setFont(header_font)
        self.results_label.setStyleSheet(f'color: {header_color};')

        self.results_table = QTableView()
        self.results_model = PandasModel(pd.DataFrame(columns=self.df.columns))
        self.results_table.setModel(self.results_model)
        self.results_table.setFont(QFont('Segoe UI', 11))
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setMinimumSectionSize(90)
        self.results_table.horizontalHeader().setDefaultSectionSize(120)
        self.results_table.setWordWrap(False)
        self.results_table.setStyleSheet("QTableView { font-size: 11pt; } QHeaderView::section { font-size: 11pt; font-weight: bold; padding: 6px 12px; }")

        self.obj_display = QLineEdit()
        self.obj_display.setReadOnly(True)
        self.last_results_df = pd.DataFrame(columns=self.df.columns)
        self.last_obj_val = None

        right_top = QVBoxLayout()
        header_lbl = QLabel('Experiments Dataset')
        header_lbl.setFont(header_font)
        header_lbl.setStyleSheet(f'color: {header_color};')
        right_top.addWidget(header_lbl)
        right_top.addWidget(self.table)

        obj_label = QLabel('Objective Value')
        obj_label.setFont(header_font)
        obj_label.setStyleSheet(f'color: {header_color};')
        obj_form = QFormLayout()
        obj_form.addRow(obj_label, self.obj_display)
        right_top.addLayout(obj_form)

        right_top.addWidget(self.results_label)
        right_top.addWidget(self.results_table)

        main_layout = QHBoxLayout()
        main_layout.addWidget(left_box, 1)
        main_layout.addLayout(right_top, 3)
        self.setLayout(main_layout)

        self._viz_window = None

    def open_visualization_window(self):
        if self._viz_window is None or not self._viz_window.isVisible():
            self._viz_window = VisualizationWindow(self)
            self._viz_window.show()
        else:
            self._viz_window.raise_()
            self._viz_window.activateWindow()

    
    def add_experiment(self):
        existing_experiments = list(zip(self.df['id'].astype(str).tolist(), self.df['name'].astype(str).tolist()))
        dlg = AddExperimentDialog(existing_experiments, self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            new_id = next_enumber_id(self.df, prefix='E')

            row = {c: '' for c in self.df.columns}
            row['id'] = new_id
            row['name'] = data['name']
            row['value'] = data['value']
            row['lab_hours'] = data['lab_hours']
            row['human_hours'] = data['human_hours']
            row['cost_usd'] = data['cost_usd']
            row['reagent_A_ml'] = data['reagent_A_ml']
            row['reagent_B_g'] = data['reagent_B_g']
            row['reagent_C_mmol'] = data['reagent_C_mmol']
            row['instr_HPLC'] = data['instr_HPLC']
            row['instr_GC'] = data['instr_GC']
            row['instr_Microscope'] = data['instr_Microscope']
            row['instr_MassSpec'] = data['instr_MassSpec']
            row['safety_level'] = data['safety_level']
            row['dependencies'] = data['dependencies']

            self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
            self.df = self.df[REQUIRED_COLUMNS]
            self.model.update(self.df)
            try:
                if self.dataset_path:
                    save_dataset(self.df, self.dataset_path)
            except Exception:
                pass
            QMessageBox.information(self, 'Added', f"Experiment '{data['name']}' added with id {new_id}.")

    def gather_thresholds(self) -> Dict:
        benches = int(self.benches_spin.value())
        techs = int(self.techs_spin.value())
        lab_hours = benches * 5 * 8
        human_hours = techs * 5 * 8

        safety_limits = {}
        for lvl, sb in self.safety_spins.items():
            v = int(sb.value())
            if v > 0:
                safety_limits[lvl] = v

        return {
            'total_lab_hours_per_week': float(lab_hours),
            'total_budget_usd': float(self.budget_spin.value()),
            'reagent_A_ml_available': float(self.reagA_spin.value()),
            'reagent_B_g_available': float(self.reagB_spin.value()),
            'reagent_C_mmol_available': float(self.reagC_spin.value()),
            'human_hours_available': float(human_hours),
            'instrument_counts': {
                'instr_HPLC': int(self.hplc_spin.value()),
                'instr_GC': int(self.gc_spin.value()),
                'instr_Microscope': int(self.mic_spin.value()),
                'instr_MassSpec': int(self.ms_spin.value()),
            },
            'safety_limits': safety_limits
        }

    def solve_model(self):
        thresholds = self.gather_thresholds()
        try:
            res_df, info = build_and_solve_gurobi(self.df, thresholds, time_limit=30)

            # store for export
            self.last_results_df = res_df.copy() if not res_df.empty else pd.DataFrame(columns=self.df.columns)
            self.last_obj_val = info.get('obj_val', None)

            if res_df.empty:
                self.results_model.update(pd.DataFrame(columns=self.df.columns))
                self.obj_display.setText('N/A')
                QMessageBox.information(self, 'Result', 'No experiments selected by the optimizer (check constraints).')
            else:
                self.results_model.update(res_df)
                obj = info.get('obj_val', None)
                if obj is not None:
                    self.obj_display.setText(f'{obj:.2f}')
                    QMessageBox.information(self, 'Result', f"Objective value: {obj:.2f}\nSelected experiments: {', '.join(res_df['id'].tolist())}")
                else:
                    self.obj_display.setText('N/A')
                    QMessageBox.information(self, 'Result', f"Selected experiments: {', '.join(res_df['id'].tolist())}")
        except Exception as e:
            tb = traceback.format_exc()
            QMessageBox.critical(self, 'Solve error', f'An error occurred while solving:\n{e}\n\n{tb}')

def apply_light_palette(app: QApplication):
    app.setStyle('Fusion')
    p = QPalette()
    p.setColor(QPalette.Window, QColor(250, 250, 250))
    p.setColor(QPalette.WindowText, QColor(0, 0, 0))
    p.setColor(QPalette.Base, QColor(245, 245, 245))
    p.setColor(QPalette.AlternateBase, QColor(255, 255, 255))
    p.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    p.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    p.setColor(QPalette.Text, QColor(0, 0, 0))
    p.setColor(QPalette.Button, QColor(240, 240, 240))
    p.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    p.setColor(QPalette.Highlight, QColor(76, 175, 80))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(p)
    app.setStyleSheet("QToolTip { color: #000000; background-color: #ffffe1; border: 1px solid black; }")