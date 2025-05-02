import subprocess
import os

COMMAND_BASE = [
        "../.././ns3",
        "run",
        "scratch/Traffic-Policing-Inference-Simulation/WeHeY-simulation-shaping.cc"
        ]

def run_simulation_shaping(burst, queueSize):
    command = COMMAND_BASE + [
        "--",
        f"--burst={burst}",
        f"--queueSize={queueSize}"
    ]
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error during simulation:", e.stderr)

def run_shaping_exp():
    
    outRate = 2 * 10**6 # 2 Mbps
    rtt = 5 * 4 * 10**-3 # 5ms one link, total return time is 20ms
    bdp = outRate * rtt / 8 # 2Mbps * 20ms / 8b = 5000B
    queueAddition = "B"
    
    bursts = [1500, 500000] # approx 1 packet and 500 packets
    
    queueFactors = [0.1, 2]
    queueSizes = []
    for factor in queueFactors:
        print(f"computed queue size: {factor * bdp}{queueAddition}")
        queueSizes.append(f"{factor * bdp}{queueAddition}")
    
    i = 0
    size = len(bursts) * len(queueSizes)
    for b in bursts:
        for q in queueSizes:
            print(f"Running simulation with burst: {b}, queueSize: {q} | {i+1}/{size}")
            run_simulation_shaping(b, q)
            print("Simulation completed.\n")
            i += 1
    print("All simulations completed.") 
    

if __name__ == "__main__":
    run_shaping_exp()
    