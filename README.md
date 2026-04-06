# MKP-ExperimentScheduler

A Python GUI application to schedule R&D experiments using a **Multidimensional Knapsack Problem (MKP)** solver (Gurobi). It helps plan lab resources, budget, reagents and equipment efficiently.

## Features

- Load and manage experiments dataset (CSV)
- Add new experiments with dependencies
- Solve scheduling optimization using Gurobi
- Visualize resource utilization and safety-level distribution
- User-friendly PySide6 GUI

## Tech Stack

### Core Technologies
- **Python 3.8+** - Primary language
- **PySide6 (Qt6)** - Desktop GUI framework
- **Gurobi** - Mathematical optimization solver
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing
- **Matplotlib** - Data visualization

### Architecture
- **Desktop Application** - Runs locally on user's machine
- **CSV-based Storage** - Simple file-based data persistence
- **Mathematical Optimization** - Solves MKP using mixed-integer programming

## Installation

### Prerequisites
- Python 3.8 or higher
- Gurobi Optimizer (free academic license available)
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/ghaidabs/MKP-ExperimentScheduler.git
   cd MKP-ExperimentScheduler
   ```

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install PySide6 pandas numpy matplotlib gurobipy
   ```

4. **Install and License Gurobi**
   - Download from: https://www.gurobi.com/downloads/gurobi-software/
   - Install: `pip install gurobipy`
   - Obtain license key (free for academic use): https://www.gurobi.com/free-academic-license/
   - Set up license: `gurobi_cl --license`

## Usage

### Running the Application

```bash
python main.py
```

The application will launch with a maximized window displaying the experiment scheduler interface.

### Workflow

1. **View Experiments Dataset**
   - Left panel shows all available experiments in a table
   - Each experiment has properties like lab hours, cost, reagents, and instruments needed

2. **Configure Resource Thresholds**
   - Set number of lab benches and techs
   - Define budget constraints
   - Specify available reagents (A, B, C)
   - Set available instruments (HPLC, GC, Microscope, MassSpec)
   - Configure safety-level limits

3. **Add New Experiments**
   - Click "Add Experiment" button
   - Fill in experiment details (name, value, resource requirements)
   - Select dependencies on other experiments
   - New experiments are automatically saved to CSV

4. **Solve Optimization Problem**
   - Click "Solve (Gurobi)" button
   - Solver finds optimal experiment schedule
   - Results display selected experiments and objective value
   - Time limit: 30 seconds

5. **Visualize Results**
   - Click "Visualize" button
   - View resource utilization (used vs available)
   - See safety-level distribution across selected experiments

## Data Format

### CSV Dataset Structure

The `dataset.csv` file contains experiments with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | String | Unique experiment identifier (e.g., E1, E2) |
| `name` | String | Experiment name/description |
| `value` | Float | Priority/benefit value (objective function) |
| `lab_hours` | Float | Lab time required |
| `human_hours` | Float | Technician time required |
| `cost_usd` | Float | Budget cost in USD |
| `reagent_A_ml` | Float | Reagent A consumption (mL) |
| `reagent_B_g` | Float | Reagent B consumption (g) |
| `reagent_C_mmol` | Float | Reagent C consumption (mmol) |
| `instr_HPLC` | Int | HPLC instrument required (0 or 1) |
| `instr_GC` | Int | Gas Chromatograph required (0 or 1) |
| `instr_Microscope` | Int | Microscope required (0 or 1) |
| `instr_MassSpec` | Int | Mass Spectrometer required (0 or 1) |
| `safety_level` | Int | Safety level (1-5) |
| `dependencies` | String | JSON array of dependent experiment IDs |

### Example Row
```csv
E1,Protein Analysis,100.5,20,15,500,50,200,1000,1,0,1,0,3,"[""E2"",""E3""]"
```

## Optimization Model

### Objective
Maximize the sum of values of selected experiments:
```
maximize: Σ(value[i] × x[i])
```

### Constraints
- **Lab Hours**: Σ(lab_hours[i] × x[i]) ≤ total_lab_hours_per_week
- **Human Hours**: Σ(human_hours[i] × x[i]) ≤ human_hours_available
- **Budget**: Σ(cost_usd[i] × x[i]) ≤ total_budget_usd
- **Reagent A**: Σ(reagent_A_ml[i] × x[i]) ≤ reagent_A_ml_available
- **Reagent B**: Σ(reagent_B_g[i] × x[i]) ≤ reagent_B_g_available
- **Reagent C**: Σ(reagent_C_mmol[i] × x[i]) ≤ reagent_C_mmol_available
- **Instruments**: Σ(instr_X[i] × x[i]) ≤ instrument_count[X]
- **Safety Limits**: Count of experiments with safety_level=k ≤ max_allowed[k]
- **Dependencies**: If x[i]=1, then x[dependent[j]]=1 for all dependencies

Where `x[i] ∈ {0, 1}` (binary: experiment selected or not)

## Project Structure

```
MKP-ExperimentScheduler/
├── main.py              # Application entry point
├── ui.py                # PySide6 GUI components & MainWindow
├── solver.py            # Gurobi optimization logic
├── data.py              # Data loading/saving & utilities
├── dataset.csv          # Experiment data storage
├── icon.png             # Application icon
└── README.md            # This file
```

### Module Details

#### `main.py`
- Entry point for the application
- Initializes Qt application
- Sets up UI theme and window properties
- Launches MainWindow

#### `ui.py`
Core GUI components:
- **PandasModel**: Qt table model for displaying DataFrames
- **AddExperimentDialog**: Dialog for creating new experiments
- **VisualizationWindow**: Charts for resource utilization and safety distribution
- **MainWindow**: Primary application window with controls and tables

#### `solver.py`
Optimization engine:
- `parse_dependencies_string()` - Parses dependency JSON strings
- `build_and_solve_gurobi()` - Main solver function that:
  - Creates Gurobi model with binary variables
  - Adds all resource and safety constraints
  - Adds dependency constraints
  - Optimizes and returns selected experiments

#### `data.py`
Data management:
- `load_dataset()` - Loads CSV file with validation
- `save_dataset()` - Persists DataFrame to CSV
- `next_enumber_id()` - Generates unique experiment IDs
- `DEFAULT_THRESHOLDS` - Default constraint values
- `REQUIRED_COLUMNS` - Dataset schema definition

## Default Thresholds

```python
{
    'total_lab_hours_per_week': 160.0,      # 4 benches × 40 hrs/week
    'human_hours_available': 200.0,         # 5 techs × 40 hrs/week
    'total_budget_usd': 25000.0,
    'reagent_A_ml_available': 5000.0,
    'reagent_B_g_available': 1500.0,
    'reagent_C_mmol_available': 8000.0,
    'instrument_counts': {
        'instr_HPLC': 5,
        'instr_GC': 2,
        'instr_Microscope': 10,
        'instr_MassSpec': 3
    },
    'safety_limits': {5: 2}  # Max 2 experiments at safety level 5
}
```

## Troubleshooting

### Gurobi License Issues
- Error: "No license found"
- Solution: Obtain free academic license from https://www.gurobi.com/free-academic-license/
- Run `gurobi_cl --license` to register

### No Experiments Selected
- Check that constraints aren't too tight
- Verify experiment values are > 0
- Review threshold values in left panel

### GUI Not Rendering Properly
- Ensure PySide6 is correctly installed: `pip install --upgrade PySide6`
- Try deleting `__pycache__` directory and rerun

### CSV File Not Found
- Application automatically creates empty dataset if file missing
- Ensure `dataset.csv` is in the same directory as `main.py`

## Future Enhancements

- [ ] Multi-period scheduling (scheduling across multiple weeks)
- [ ] Experiment templates and presets
- [ ] Export results to PDF/Excel
- [ ] Constraint sensitivity analysis
- [ ] What-if scenario modeling
- [ ] Database backend (PostgreSQL/SQLite) instead of CSV
- [ ] API layer for integration with LIMS systems
- [ ] Real-time constraint suggestions

## Requirements

```
PySide6>=6.0.0
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
gurobipy>=11.0.0
```

## License

This project is available under the MIT License. See LICENSE file for details.

## Author

**ghaidabs** - Created December 2025

## Support

For issues, questions, or contributions, please open an issue on GitHub:
https://github.com/ghaidabs/MKP-ExperimentScheduler/issues

---

**Note**: This application requires a valid Gurobi license. Gurobi offers free licenses for academic and personal use.
```

---

This README is now **accurate and complete** with:
✅ Only Python tech stack (no React/Node)
✅ Clear architecture explanation
✅ Complete installation & usage guide
✅ Data format specifications
✅ Optimization model details
✅ Troubleshooting section
✅ Project structure breakdown
