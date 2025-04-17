import matplotlib.pyplot as plt
import numpy as np


data = np.loadtxt("../../wehe-throughput.txt")
time = data[:, 0]    # Time in seconds
throughput = data[:, 1]  # Throughput in Mbps

plt.plot(time, throughput, linestyle="-")
plt.xlabel("Time (s)")
plt.ylabel("Throughput (Mbps)")
plt.title("Throughput Over Time")
plt.grid()
plt.savefig("throughput_plt")
# plt.show()
