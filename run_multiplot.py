import pandas as pd
import matplotlib as plt
from analysis_utils import clean_colums, multiplot_estimated_rate

file = "data/results_reno-complex-shaping_CUMULATIVE.csv"
df_reno_cum_var = pd.read_csv(file)
df_reno_cum_var = clean_colums(df_reno_cum_var)
df_reno_cum_var = df_reno_cum_var[df_reno_cum_var['queue_size'] <= 5]
df_reno_cum_var = df_reno_cum_var[df_reno_cum_var['queue_size'] >= 0.5]

file = "data/results_reno-xtopo_CUMULATIVE.csv"
df_reno_cum_xtopo_20 = pd.read_csv(file)
df_reno_cum_xtopo_20 = clean_colums(df_reno_cum_xtopo_20, xtopo=True)
df_reno_cum_xtopo_20 = df_reno_cum_xtopo_20[df_reno_cum_xtopo_20['queue_size'] >= 0.5]
df_reno_cum_xtopo_20 = df_reno_cum_xtopo_20[df_reno_cum_xtopo_20['queue_size'] <= 5]


file = "data/results_xtopo-2.0_CUMULATIVE.csv"
df_cum_xtopo_20 = pd.read_csv(file)
df_cum_xtopo_20 = clean_colums(df_cum_xtopo_20, xtopo=True)
df_cum_xtopo_20 = df_cum_xtopo_20[df_cum_xtopo_20['queue_size'] >= 0.5]
df_cum_xtopo_20 = df_cum_xtopo_20[df_cum_xtopo_20['queue_size'] <= 5]

file = "data/results_reno-complex-shaping_CUMULATIVE.csv"
df_cum_var = pd.read_csv(file)
df_cum_var = clean_colums(df_cum_var)
df_cum_var = df_cum_var[df_cum_var['queue_size'] <= 5]
df_cum_var = df_cum_var[df_cum_var['queue_size'] >= 0.5]


dfs = [
    df_cum_var,
    df_cum_xtopo_20,
    df_reno_cum_var,
    df_reno_cum_xtopo_20
]

titles = [
    'Cumulative Arrival Derivative Estimation\n(Simple topology, variable-sized, TCP NewReno)',
    'Cumulative Arrival Derivative Estimation\n(X topology, ratio 2:1, TCP NewReno)',
]

multiplot_estimated_rate(dfs, titles, y_min=-0.1, y_max=4, nrows=2, ncols=2, figsize=(15,8), log=False,save_path="figures/estimated_rate_cumulative_reno_compare.png")

