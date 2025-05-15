import utils
import pandas as pd
import os
import math

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


class ExperimentRun:
    def __init__(self, name, server_pcap, client_pcap, metadata_file, params):
        self.name = name
        self.server_pcap = server_pcap
        self.client_pcap = client_pcap
        self.metadata_file = metadata_file
        self.params = params
        self.metadata = self.get_metadata_info()

    def get_pcap_df(self):
        return utils.get_lossEvents_from_server_client_pcaps(
            self.server_pcap, self.client_pcap, SERVER_PORT)
        
    def get_metadata_info(self):
       with open(self.metadata_file, 'r') as f:
            lines = f.readlines()
            metadata = [float(lines[0]), int(lines[1])]
            return metadata
        
    def get_client_rx_throughput(self):
        fields = {
            'frame.time_relative': 'time', 'tcp.seq': 'seq', 'ip.len': 'length', 'tcp.len': 'tcp_length',
            'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
            'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
            'tcp.ack': 'ack'
        }
        
        pkt_filter = "tcp.srcport=={}".format(SERVER_PORT)

        client_df = utils.pcap_to_df(self.client_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
        # client_df = preprocess_df(client_df)
        
        if client_df.empty:
            return 0
        data_rx = client_df['length'].sum() # ip.len
        first_packet_time = client_df['time'].iloc[0]
        last_packet_time = client_df['time'].iloc[-1]
        elapsed_time = last_packet_time - first_packet_time
        throughput = data_rx / elapsed_time * 8 # convert to bps
        return throughput
    
    def __repr__(self):
        return f"ExperimentRun(name={self.name}, server_pcap={self.server_pcap}, client_pcap={self.client_pcap}, metadata_file={self.metadata_file}, params={self.params})"
    
def get_first_and_last_loss_index(df):
    lost_indices = df[df['is_lost'] == True].index
    if lost_indices.empty:
        raise ValueError("No lost packets found.")
    return lost_indices[0], lost_indices[-1]


def get_policing_rate(df, p_first, p_last):
    time_between_loss = df.iloc[p_last]['timestamp'] - \
        df.iloc[p_first]['timestamp']

    sum_delivered = 0
    counter = 0
    for i in range(p_first, p_last + 1):
        if not df.iloc[i]['is_lost']:
            sum_delivered += df.iloc[i]['pkt_len']
            counter += 1
    
    print("total sum delivered: ", sum_delivered)
    # print("average received packet size: ", sum_delivered / counter)
    return sum_delivered / time_between_loss * 8 # convert to bps

def get_policing_rate_delayed(df, p_first, p_last, delay):
    t_loss_start = df.iloc[p_first]['timestamp'] + delay
    t_loss_end = df.iloc[p_last]['timestamp'] + delay
    print("start: ", t_loss_start, " end: ", t_loss_end)
    time_between_loss = t_loss_end - t_loss_start
    
    sum_delivered = 0
    df = df.sort_values('timestamp')
    
    for _, row in df.iterrows():
        if row['is_lost'] or (row['timestamp'] <= t_loss_start or row['timestamp'] >= t_loss_end):
            print("dropped: lost? ", row.is_lost, "\t time: ", row.timestamp)
            continue
        sum_delivered += row['pkt_len']
        
    print("total sum delivered: ", sum_delivered)

    return sum_delivered / time_between_loss

def was_policing_happening(lost_list, passed_list, noise_loss=0.1, noise_passed=0.03):
    avg_loss = sum(lost_list) / len(lost_list)
    avg_passed = sum(passed_list) / len(passed_list)
    median_loss = sorted(lost_list)[len(lost_list) // 2]
    median_passed = sorted(passed_list)[len(passed_list) // 2]
    print(f"loss is less than passed: {avg_loss < avg_passed}")
    print(f"median loss is less than passed: {median_loss < median_passed}")
    # add count of vals close to 0 in lost_list, and vals positive in passed_list compared to noise adjustments
    # and maybe check the RTT increase before the first loss packet
    return False

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


def get_experiment_runs(exp_name):
    files = [f for f in os.listdir(DATA) if os.path.isfile(os.path.join(DATA, f))]
    runs = []
    for file in files:
        file_parts = file.split('_')
        if (not exp_name in file_parts) or (not METADATA_FILE in file_parts):
            continue
        file_parts = [part for part in file_parts if part]
        file_params = file_parts[3:]
        name = str.join('_',file_params)
        sim_file_start = os.path.join(DATA, file.replace(METADATA_FILE, SIM_FILE))
        server_pcap = "".join([sim_file_start, SERVER_IDENTIFIER])
        client_pcap = "".join([sim_file_start, CLIENT_IDENTIFIER])
        # server_pcap = os.path.join(DATA, server_pcap_name)
        # client_pcap = os.path.join(DATA, client_pcap_name)
        
        run = ExperimentRun(
            name=name,
            server_pcap=server_pcap,
            client_pcap=client_pcap,
            metadata_file=os.path.join(DATA, file),
            params=file_params
        )
        runs.append(run)
    return runs

def is_correct_num_lost(df, expected_lost):
    return (( df[df['is_lost']== True].shape[0] - expected_lost) / expected_lost, (df[df['is_lost']== True].shape[0] - expected_lost) / expected_lost)

def is_correct_rate(rate, expected_rate):
    return ((rate - expected_rate) / expected_rate, abs(rate - expected_rate) / expected_rate)

def analyse_run(run):
    pcap_df = run.get_pcap_df()
    throughput = run.get_client_rx_throughput()
    print(f"Throughput at rx: {throughput}")
    num_lost = pcap_df[pcap_df['is_lost']== True].shape[0]
    
    if num_lost > 0 and run.metadata[1] == 0:
        print(f"FALSE POSITIVE: Lost packets detected ({num_lost})but no expected lost packets.")
    
    if num_lost < 15 or run.metadata[1] == 0:
        return {"burst": run.params[0], "queue_size": run.params[1], "rate": 0, "lost": num_lost, "error_lost": 0, "error_lost_abs": 0, "error_rate": 1, "error_rate_abs": 1, "actual_rate": run.metadata[0], "rx_rate": throughput}
 
    error_lost, error_lost_abs = is_correct_num_lost(pcap_df, run.metadata[1]) 
    
    p_first, p_last = get_first_and_last_loss_index(pcap_df)
    rate = get_policing_rate(pcap_df, p_first, p_last)
    
    if throughput == 0:
        error_rate = 1
        error_rate_abs = 1
    else:
        error_rate, error_rate_abs = is_correct_rate(rate, throughput)
        if abs(rate - run.metadata[0]) > 0:
            print(f"Rate error: {error_rate}, Rate: {rate}, Expected rate: {throughput}")
    
    
        
    return {"burst": run.params[0], "queue_size": run.params[1], "rate": rate, "lost": num_lost, "error_lost": error_lost, "error_lost_abs": error_lost_abs, "error_rate": error_rate, "error_rate_abs": error_rate_abs,"actual_rate": run.metadata[0], "rx_rate": throughput}
    

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

def save_results(results, exp_name):
    df = pd.DataFrame(results)
    df.to_csv(f"{DATA}results_{exp_name}.csv", index=False)
    print(f"Results saved to results_{exp_name}.csv")

def experiment_analysis(exp_name): 
    # TODO: if exp_name == EXP_XTOPO, then CLIENT_IDENTIFIER is different from 'n1-n2-2-0.pcap'
    runs = get_experiment_runs(exp_name)
    results = []
    index = 1
    for run in runs:
        print(f"run {index}/{len(runs)} : {run.name}")
        if 'p' in run.name:
            continue
        estimation = analyse_run(run)
        results.append(estimation)

        index += 1
        # print(f"Run: {run.name}, Policing Rate: {estimation['rate']}, Lost Packets: {estimation['lost']}, Error in Lost Packets: {estimation['error_lost']}, Error in Policing Rate: {estimation['error_rate']}")
    results_analysis(results)
    save_results(results, exp_name)
    
# experiment_analysis(EXP_SHAPING_COMPLEX)
# experiment_analysis(EXP_SHAPING)
experiment_analysis(EXP_XTOPO)
exit(0)

real_lost_packets = get_lost_packets(DROPPED_PACKETS_NS3)

# pcap_df = utils.get_lossEvents_from_pcap(SERVER_PCAP, SERVER_PORT)
# pcap_df1 = utils.get_lossEvents_from_hashes(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT, real_lost_packets)
# pcap_df = utils.get_lossEvents_from_hashes(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT)
pcap_df = utils.get_lossEvents_from_server_client_pcaps(SERVER_PCAP, CLIENT_PCAP, SERVER_PORT)
# pcap_df = utils.generate_random_loss_df(num_packets=1000)

compare_lost_with_real(pcap_df[pcap_df['is_lost']== True], real_lost_packets)

print("pcap_df with loss events: ", pcap_df.shape)

p_first, p_last = get_first_and_last_loss_index(pcap_df)

print("first and last index: ", p_first, p_last)
rate = get_policing_rate(pcap_df, p_first, p_last)

# rate = get_policing_rate_delayed(pcap_df, p_first, p_last, PROPAGATION_DELAY)
print(f"Goodput: {rate * 8} bps")


t_used = 0
t_available = 0
lost_list = []
passed_list = []
# between the first and last lost packet, all packets used tokens
for i in range(p_first + 1, p_last):
    p_current = pcap_df.iloc[i]
    t_produced = rate * \
        (p_current['timestamp'] - pcap_df.iloc[p_first]
         ['timestamp'])
    t_available = t_produced - t_used
    if p_current['is_lost']:
        lost_list.append(t_available)
    else:
        passed_list.append(t_available)
        t_used += p_current['pkt_len']

print(f"avaiable size at the end: {t_available} B")
print(f"used total bytes at the end: {t_used} B")

# was_policing_happening(lost_list, passed_list)
