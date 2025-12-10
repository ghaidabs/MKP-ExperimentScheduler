import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from typing import Dict, List, Tuple

from data import DEFAULT_THRESHOLDS


def parse_dependencies_string(s: str) -> List[str]:
    if not s:
        return []
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    if not s:
        return []
    parts = [p.strip() for p in s.split(',') if p.strip()]
    return parts


def build_and_solve_gurobi(df: pd.DataFrame, thresholds: Dict, time_limit: int = 30) -> Tuple[pd.DataFrame, Dict]:
    m = gp.Model('multidim_knapsack')
    m.setParam('OutputFlag', 0)
    m.setParam('TimeLimit', time_limit)

    ids = list(df['id'])
    x = {i: m.addVar(vtype=GRB.BINARY, name=f'x_{i}') for i in ids}
    values = df.set_index('id')['value'].to_dict()
    m.setObjective(gp.quicksum(values[i] * x[i] for i in ids), GRB.MAXIMIZE)

    def coldict(col):
        return df.set_index('id')[col].to_dict()

    lab_hours = coldict('lab_hours')
    human_hours = coldict('human_hours')
    cost_usd = coldict('cost_usd')
    reagent_A = coldict('reagent_A_ml')
    reagent_B = coldict('reagent_B_g')
    reagent_C = coldict('reagent_C_mmol')
    instr_HPLC = coldict('instr_HPLC')
    instr_GC = coldict('instr_GC')
    instr_Mic = coldict('instr_Microscope')
    instr_MS = coldict('instr_MassSpec')
    safety = coldict('safety_level')

    m.addConstr(gp.quicksum(lab_hours[i] * x[i] for i in ids) <= thresholds.get('total_lab_hours_per_week', DEFAULT_THRESHOLDS['total_lab_hours_per_week']), name='lab_hours')
    m.addConstr(gp.quicksum(human_hours[i] * x[i] for i in ids) <= thresholds.get('human_hours_available', DEFAULT_THRESHOLDS['human_hours_available']), name='human_hours')
    m.addConstr(gp.quicksum(cost_usd[i] * x[i] for i in ids) <= thresholds.get('total_budget_usd', DEFAULT_THRESHOLDS['total_budget_usd']), name='budget')
    m.addConstr(gp.quicksum(reagent_A[i] * x[i] for i in ids) <= thresholds.get('reagent_A_ml_available', DEFAULT_THRESHOLDS['reagent_A_ml_available']), name='reagent_A')
    m.addConstr(gp.quicksum(reagent_B[i] * x[i] for i in ids) <= thresholds.get('reagent_B_g_available', DEFAULT_THRESHOLDS['reagent_B_g_available']), name='reagent_B')
    m.addConstr(gp.quicksum(reagent_C[i] * x[i] for i in ids) <= thresholds.get('reagent_C_mmol_available', DEFAULT_THRESHOLDS['reagent_C_mmol_available']), name='reagent_C')

    instr_counts = thresholds.get('instrument_counts', DEFAULT_THRESHOLDS['instrument_counts'])
    m.addConstr(gp.quicksum(instr_HPLC[i] * x[i] for i in ids) <= instr_counts.get('instr_HPLC', 0), name='instr_HPLC')
    m.addConstr(gp.quicksum(instr_GC[i] * x[i] for i in ids) <= instr_counts.get('instr_GC', 0), name='instr_GC')
    m.addConstr(gp.quicksum(instr_Mic[i] * x[i] for i in ids) <= instr_counts.get('instr_Microscope', 0), name='instr_Microscope')
    m.addConstr(gp.quicksum(instr_MS[i] * x[i] for i in ids) <= instr_counts.get('instr_MassSpec', 0), name='instr_MassSpec')

    safety_limits = thresholds.get('safety_limits', DEFAULT_THRESHOLDS.get('safety_limits', {}))
    safety_limits_normalized = {}
    for k, v in safety_limits.items():
        try:
            lvl = int(k)
            safety_limits_normalized[lvl] = int(v)
        except Exception:
            continue

    for lvl, max_allowed_count in safety_limits_normalized.items():
        if max_allowed_count <= 0:
            continue
        ids_at_level = [i for i in ids if int(safety.get(i, 0)) == lvl]
        if ids_at_level:
            m.addConstr(gp.quicksum(x[i] for i in ids_at_level) <= max_allowed_count,
                        name=f'max_level_{lvl}')

    for idx, row in df.iterrows():
        i = str(row['id'])
        deps_raw = str(row.get('dependencies', '')).strip()
        deps = parse_dependencies_string(deps_raw)
        for dep in deps:
            if dep in x:
                m.addConstr(x[i] <= x[dep], name=f'dep_{i}_{dep}')

    m.optimize()

    selected = []
    if m.status in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        for i in ids:
            try:
                val = x[i].X
            except Exception:
                val = 0
            if val > 0.5:
                selected.append(i)

    result_df = df[df['id'].isin(selected)].copy()
    result_info = {'status': m.status, 'obj_val': m.objVal if m.status in (GRB.OPTIMAL, GRB.TIME_LIMIT) else None}
    return result_df, result_info