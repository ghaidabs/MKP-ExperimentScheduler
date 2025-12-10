import os
import re
import pandas as pd
from typing import Tuple, Optional


DEFAULT_THRESHOLDS = {
    'total_lab_hours_per_week': 160.0,
    'total_budget_usd': 25000.0,
    'reagent_A_ml_available': 5000.0,
    'reagent_B_g_available': 1500.0,
    'reagent_C_mmol_available': 8000.0,
    'human_hours_available': 200.0,
    'instrument_counts': {'instr_HPLC': 5, 'instr_GC': 2, 'instr_Microscope': 10, 'instr_MassSpec': 3},
    'safety_limits': {5: 2},
}

REQUIRED_COLUMNS = [
    'id', 'name', 'value', 'lab_hours', 'cost_usd', 'reagent_A_ml', 'reagent_B_g', 'reagent_C_mmol',
    'instr_HPLC', 'instr_GC', 'instr_Microscope', 'instr_MassSpec', 'human_hours', 'safety_level', 'dependencies'
]



def load_dataset(path: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_path = os.path.join(script_dir, 'dataset.csv')
    used = path or default_path

    if os.path.exists(used):
        df = pd.read_csv(used)
    else:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            if col in ['id', 'name', 'dependencies']:
                df[col] = ''
            else:
                df[col] = 0

    numeric_cols = ['value', 'lab_hours', 'cost_usd', 'reagent_A_ml', 'reagent_B_g', 'reagent_C_mmol',
                    'human_hours', 'safety_level', 'instr_HPLC', 'instr_GC', 'instr_Microscope', 'instr_MassSpec']
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df['id'] = df['id'].astype(str)
    df['name'] = df['name'].fillna('').astype(str)
    df['dependencies'] = df['dependencies'].fillna('').astype(str)
    df = df[REQUIRED_COLUMNS]
    return df, used


def save_dataset(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)


def next_enumber_id(df: pd.DataFrame, prefix: str = 'E') -> str:
    max_n = 0
    pattern = re.compile(rf'^{re.escape(prefix)}([0-9]+)$', re.IGNORECASE)

    for i in df['id'].astype(str):
        m = pattern.match(i.strip())
        if m:
            n = int(m.group(1))
            if n > max_n:
                max_n = n

    return f"{prefix}{max_n + 1}"