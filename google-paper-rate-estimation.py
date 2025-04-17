import utils
import pandas as pd

PCAP_FILE = '../../wehe-0-0.pcap'

# SERVER_PCAP = '../../wehe-0-0.pcap'
# CLIENT_PCAP = '../../wehe-1-0.pcap'
SERVER_PCAP = '../../wehe_n0-n1-0-0.pcap'
CLIENT_PCAP = '../../wehe_n1-n2-2-0.pcap'

DROPPED_PACKETS_NS3 = '../../wehe-dropped-packets.txt'


PKT_LEN = 1502 * 8 # MTU * 8bits
LINK_RATE = 20e6 # 20Mb/s 
PROPAGATION_DELAY = PKT_LEN / LINK_RATE
print(PROPAGATION_DELAY)

SERVER_PORT = 49153


def get_first_and_last_loss_index(df):
    lost_indices = df[df['is_lost'] == True].index
    if lost_indices.empty:
        raise ValueError("No lost packets found.")
    return lost_indices[0], lost_indices[-1]


def get_policing_rate(df, p_first, p_last):
    time_between_loss = df.iloc[p_last]['timestamp'] - \
        df.iloc[p_first]['timestamp']

    sum_delivered = 0
    for i in range(p_first, p_last + 1):
        if not df.iloc[i]['is_lost']:
            sum_delivered += df.iloc[i]['pkt_len']
    
    print("total sum delivered: ", sum_delivered)
    return sum_delivered / time_between_loss

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
