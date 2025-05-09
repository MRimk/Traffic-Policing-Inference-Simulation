import pandas as pd
import matplotlib as mpl
import re

mpl.use('WebAgg')
mpl.rcParams['webagg.open_in_browser'] = False
mpl.rcParams['webagg.port'] = 9000       # pick any free port you like
# mpl.rcParams['webagg.port_retries'] = 0  # if you only want exactly that port

# 3) Switch to WebAgg **before** importing pyplot
mpl.use('WebAgg')

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D   # registers the 3-D projection


file = "data/results_shaping.csv"
df = pd.read_csv(file)

def parse_queue_size(s):
    num = re.match(r'([\d.]+)', str(s)).group(1)
    return float(num)

df["queue_size_bytes"] = df["queue_size"].apply(parse_queue_size)

#3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")
ax.scatter(df["burst"],
           df["queue_size_bytes"],
           df["actual_rate"])

ax.set_xlabel("Burst (B)")
ax.set_ylabel("Queue size (B)")
ax.set_zlabel("Actual rate (bps)")
ax.set_title("Actual Rate vs Burst & Queue Size")
plt.show()


#2D plot
plt.figure()
sc = plt.scatter(df["burst"],
                 df["queue_size_bytes"],
                 c=df["actual_rate"],
                 s=30,                 # marker size
                 alpha=0.8)
plt.xlabel("Burst (B)")
plt.ylabel("Queue size (B)")
plt.title("Actual Rate coloured by value")
plt.colorbar(sc, label="Actual rate (bps)")
plt.tight_layout()
plt.show()