import subprocess
import os
import argparse
import time

COMMAND_BASE = [
        "../.././ns3",
        "run",
        "scratch/Traffic-Policing-Inference-Simulation/WeHeY-simulation-"
        ]

COM_SHAPING = "shaping"
COM_SHAPING_COMPLEX = "complex-shaping"
COM_YTOPO = "two-servers"

START_TIME = time.time()

def get_complete_command(command):
    complete = COMMAND_BASE
    complete[2] = complete[2] + command
    return complete

def run_build():
    command = ["../.././ns3", "build"]
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error during build:", e.stderr)
        
def process_results(arg):
    command = ["python3", "google-paper-rate-estimation.py",
               "--command", arg]
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error during result processing:", e.stderr)

def run_simulation_oneshot(burst, queueSize, ratio, command_name, command_base=COMMAND_BASE):
    command = command_base + [
        "--",
        f"--burst={burst}",
        f"--queueSize={queueSize}"
    ]
    if command_name == COM_YTOPO:
        command.append(f"--trafficRatio={ratio}")
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as e:
        print(f"Command timed out after {e.timeout} seconds")
    except subprocess.CalledProcessError as e:
        print("Error during simulation:", e.stderr)
    

def run_exp(command):
    
    command_base = get_complete_command(command)
    
    link_count = 3 if command == COM_YTOPO else 2
    
    outRate = 2 * 10**6 # 2 Mbps
    rtt = 5 * link_count * 2 * 10**-3 # 5ms one link, total return time is 20ms
    bdp = outRate * rtt / 8 # 2Mbps / 8b * 20ms = 5000B
    queueAddition = "B"
    
    onePacket = 1500 # 1500B
    burstFactors = [0.5, 1, 5, 25, 100]
    # burstFactors = [5, 25, 100]
    # burstFactors = [100]
    bursts = []
    for factor in burstFactors:
        print(f"computed burst size: {factor * onePacket}B")
        bursts.append(f"{factor * onePacket}B")
    
    packetSizeFactor = onePacket / bdp  
    # queueFactors = [0.1, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3, 5, 10, 20, 25, 30, 35, 40, 50, 100]
    queueFactors = [3, 5]
    queueSizes = []
    for factor in queueFactors:
        print(f"computed queue size: {factor * bdp}{queueAddition}")
        queueSizes.append(f"{factor * bdp}{queueAddition}")
    
    ratios = []
    if command == COM_YTOPO:
        ratios = [0.5, 1.0, 2.0]
    else:
        ratios = [1.0]
    
    i = 1
    size = len(bursts) * len(queueSizes) * len(ratios)
    average_elapsed_time = 0.0
    sum_elapsed_time = 0.0
    for r in ratios:
        for b in bursts:
            for q in queueSizes:
                print(f"Running simulation with burst: {b}, queueSize: {q}, ratio: {r} | {i}/{size}")
                last_time = time.time()
                run_simulation_oneshot(b, q, r, command, command_base)
                current_time = time.time()
                elapsed_time = current_time - last_time
                sum_elapsed_time += elapsed_time
                average_elapsed_time = sum_elapsed_time / i
                estimated_finish = START_TIME + average_elapsed_time * size 
                finish_time = time.strftime('%H:%M:%S', time.localtime(estimated_finish))
                print(f"\nElapsed time for this simulation: {elapsed_time:.2f} seconds. Estimated finish time: {finish_time} (hh:mm:ss)\n")
                i += 1
                # delete_unnecessary_files()
                
    print("All simulations completed.") 
    
def delete_unnecessary_files():
    command = [
        "find", ".", "-type", "f",
        "(", "-name", "*.pcap", "-o", "-name", "*.tr", ")",
        "!", "(", "-name", "*n0-n1-2-0.pcap", "-o", "-name", "*n1-n2-0-0.pcap", ")",
        "-delete"
    ]
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error during file deletion:", e.stderr)
    
def get_remaining_space():
    print("Simulation completed. Running df -H to check disk space.")
    
    command = ["df", "-H"]
    try:
        subprocess.run(command, cwd=os.path.dirname(__file__), check=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error during disk space check:", e.stderr)
        
def get_current_time():
    print(time.strftime('%H:%M:%S', time.localtime(time.time())))
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ns-3 simulation.")
    parser.add_argument(
        "--command",
        choices=[COM_SHAPING, COM_SHAPING_COMPLEX, COM_YTOPO],
        required=True,
        help="Command to run the simulation."
    )
    
    get_current_time()
    
    run_build()
    args = parser.parse_args()
    run_exp(args.command)
    if args.command == COM_YTOPO:
        args.command = "xtopo"
    
    process_results(args.command)
    get_remaining_space()
