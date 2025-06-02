import utils
import pandas as pd
import os
import math
import argparse
import re

from google_rate_est import *
from explore_rate_est import *
from experimentRun import *

PCAP_FILE = '../../wehe-0-0.pcap'

# SERVER_PCAP = '../../wehe-0-0.pcap'
# CLIENT_PCAP = '../../wehe-1-0.pcap'
SERVER_PCAP = '../../wehe_complex_n0-n1-0-0.pcap'
CLIENT_PCAP = '../../wehe_complex_n1-n2-2-0.pcap'


SERVER_IDENTIFIER = 'n0-n1-0-0.pcap'
CLIENT_IDENTIFIER = 'n1-n2-2-0.pcap'

METADATA_FILE = 'metadata'
SIM_FILE = 'sim'

EXP_SHAPING = 'shaping'
EXP_SHAPING_COMPLEX = 'complex-shaping'
EXP_XTOPO = 'xtopo'

DATA = "data/"

DROPPED_PACKETS_NS3 = '../../wehe-dropped-packets.txt'


PKT_LEN = 1502 * 8 # MTU * 8bits
LINK_RATE = 20e6 # 20Mb/s 
PROPAGATION_DELAY = PKT_LEN / LINK_RATE
print(PROPAGATION_DELAY)

SERVER_PORT = 49153

def get_lost_packets(txtFile):
    column_names = ['timestamp', 'seq', 'pkt_len']
    df = pd.read_csv(txtFile, header=None, names=column_names) 
    return df

def compare_lost_with_real(df_new, df_real):
    # print("columns: ", df_new.columns, "shape: ", df_new.shape)
    # print("columns: ", df_real.columns, "shape: ", df_real.shape)
    df_new['matches'] = df_new['seq'].isin(df_real['seq'])
    df_new['diff_time'] = 0.0
    df_new = df_new.reset_index(drop=True)   
    for idx, row in df_new.iterrows():
        # print(row['timestamp'] - df_real.loc[idx, 'timestamp'])
        df_new.loc[idx, 'diff_time'] = row['timestamp'] - df_real.loc[idx, 'timestamp']
    
    
    df_new = df_new.sort_values('timestamp')
    df_real = df_real.sort_values('timestamp')
    time_real = df_real['timestamp'].iloc[-1] - df_real['timestamp'].iloc[0]
    time_new = df_new['timestamp'].iloc[-1] - df_new['timestamp'].iloc[0]
    print("real elapsed time:", time_real)
    print("new elapsed time:", time_new)
    # print("new head:", df_new.head())
    # print("real head:", df_real.head())
    # print("how many don't match: ", df_new[df_new['matches'] == False].shape)

def make_pattern(keyword):
    return re.compile(rf".*{re.escape(keyword)}.*")

def get_experiment_runs(exp_name, estimation = RateEstimationMethod.GOOGLE) -> list[ExperimentRun]:
    files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA, f))]
    runs = []
    pat = make_pattern(exp_name)
    for file in files:
        file_parts = file.split('_')
        matches = [w for w in file_parts if pat.match(w)]
        if (len(matches) == 0) or (not METADATA_FILE in file_parts):
            continue
        ratio = 1.0
        if exp_name == EXP_XTOPO:
            ratio = float(file_parts[2].split('-')[1])
        file_parts = [part for part in file_parts if part]
        file_params = file_parts[3:]
        name = str.join('_',file_params)
        sim_file_start = os.path.join(DATA, file.replace(METADATA_FILE, SIM_FILE))
        server_pcap = "".join([sim_file_start, SERVER_IDENTIFIER])
        client_pcap = "".join([sim_file_start, CLIENT_IDENTIFIER])
        
        run = ExperimentRun(
            name=name,
            server_pcap=server_pcap,
            client_pcap=client_pcap,
            metadata_file=os.path.join(DATA, file),
            params=file_params,
            estimation=estimation,
            ratio=ratio
        )
        runs.append(run)
    return runs

def results_analysis(results):
    sum_rate_error = 0
    sum_lost_error = 0
    counter_rate = 0
    counter_lost = 0
    for result in results:
        sum_rate_error += result['error_rate'] if result['rate'] != 0 else 0
        counter_rate += 1 if result['rate'] != 0 else 0
        sum_lost_error += result['error_lost'] if result['lost'] != 0 else 0
        counter_lost += 1 if result['lost'] != 0 else 0
    avg_rate_error = sum_rate_error / counter_rate if counter_rate != 0 else 0
    avg_lost_error = sum_lost_error / counter_lost if counter_lost != 0 else 0
    print(f"Average rate error: {avg_rate_error}")
    print(f"Average lost error: {avg_lost_error}")

def save_results(results, exp_name, estimation=RateEstimationMethod.GOOGLE):
    df = pd.DataFrame(results)
    if exp_name == EXP_XTOPO:
        print(df)
        for ratio_value, subset in df.groupby("traffic_ratio"):
            ratio_str = str(ratio_value)
            if estimation == RateEstimationMethod.GOOGLE:
                filename = f"{DATA}results_{exp_name}-{ratio_str}.csv"
            else:
                filename = f"{DATA}results_{exp_name}-{ratio_str}_{estimation}.csv"

            subset.to_csv(filename, index=False)
            print(f"Results for trafficRatio={ratio_str} saved to {filename}")
    else:   
        name = f"{DATA}results_{exp_name}.csv" if estimation == RateEstimationMethod.GOOGLE.name else f"{DATA}results_{exp_name}_{estimation}.csv"
        df.to_csv(name, index=False)
        print(f"Results saved to {name}")

def experiment_analysis(exp_name, estimationAlg = RateEstimationMethod.GOOGLE): 
    runs = get_experiment_runs(exp_name, estimationAlg)
    results = []
    index = 1
    for run in runs:
        print(f"run {index}/{len(runs)} : {run.name}")
        if 'p' in run.name:
            continue
        estimation = analyse_run(run)
        if estimation is not None:
            results.append(estimation)
        index += 1

    results_analysis(results)
    save_results(results, exp_name, estimationAlg)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ns-3 simulation.")
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Run the simple simulation."
    )
    
    parser.add_argument(
        "--command",
        choices=[EXP_SHAPING, EXP_SHAPING_COMPLEX, EXP_XTOPO],
        required=True,
        help="Command to run the simulation."
    )
    
    est_choices = RateEstimationMethod.__members__.keys()
    
    parser.add_argument(
        "--estimation",
        choices=est_choices,
        required=True,
        help="Calculate the estimated rate using tx gaps."
    )
    
    args = parser.parse_args()
    if not args.simple:
        experiment_analysis(args.command, args.estimation)
        exit(0)
    else: 
        runs = get_experiment_runs(args.command, args.estimation)
        query_q_size = "10000.0B" # input("Enter the queue size: ")
        burst = '7500'
        for run in runs:
            if run.params[1] == query_q_size and run.params[0] == burst:
                print(f"Run: {run.name}, Policing Rate: {run.metadata[0]}, Lost Packets: {run.metadata[1]}")
                pcap_df = run.get_pcap_df()
                throughput = compute_policing_rate_avg_tx(pcap_df)
                rx = run.get_client_rx_throughput()
                print(f"Throughput at rx: {rx}")
                print(f"Policing rate: {throughput}")
                # print(f"Throughput at rx: {throughput}")
                # num_lost = pcap_df[pcap_df['is_lost']== True].shape[0]
                # print(f"Lost packets: {num_lost}")
                # p_first, p_last = get_first_and_last_loss_index(pcap_df)
                # rate = get_policing_rate(pcap_df, p_first, p_last)
                # print(f"Policing rate: {rate}")
                
    

    # real_lost_packets = get_lost_packets(DROPPED_PACKETS_NS3)

    # # pcap_df = utils.get_lossEvents_from_pcap(SERVER_PCAP, SERVER_PORT)
    # # pcap_df1 = utils.get_lossEvents_from_hashes(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT, real_lost_packets)
    # # pcap_df = utils.get_lossEvents_from_hashes(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT)
    # pcap_df = utils.get_lossEvents_from_server_client_pcaps(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT)
    # # pcap_df = utils.generate_random_loss_df(num_packets=1000)

    # compare_lost_with_real(pcap_df[pcap_df['is_lost']== True], real_lost_packets)

    # print("pcap_df with loss events: ", pcap_df.shape)

    # p_first, p_last = get_first_and_last_loss_index(pcap_df)

    # print("first and last index: ", p_first, p_last)
    # rate = get_policing_rate(pcap_df, p_first, p_last)

    # # rate = get_policing_rate_delayed(pcap_df, p_first, p_last, PROPAGATION_DELAY)
    # print(f"Goodput: {rate * 8} bps")


    # t_used = 0
    # t_available = 0
    # lost_list = []
    # passed_list = []
    # # between the first and last lost packet, all packets used tokens
    # for i in range(p_first + 1, p_last):
    #     p_current = pcap_df.iloc[i]
    #     t_produced = rate * \
    #         (p_current['timestamp'] - pcap_df.iloc[p_first]
    #         ['timestamp'])
    #     t_available = t_produced - t_used
    #     if p_current['is_lost']:
    #         lost_list.append(t_available)
    #     else:
    #         passed_list.append(t_available)
    #         t_used += p_current['pkt_len']

    # print(f"avaiable size at the end: {t_available} B")
    # print(f"used total bytes at the end: {t_used} B")

    # # was_policing_happening(lost_list, passed_list)
