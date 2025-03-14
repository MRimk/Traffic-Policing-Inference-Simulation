import utils

PCAP_FILE = 'test.pcap'
SERVER_PORT = 80

# pcap_df = utils.get_lossEvents_from_pcap(PCAP_FILE, SERVER_PORT)
pcap_df = utils.generate_random_loss_df(num_packets=1000)


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
    return sum_delivered / time_between_loss.total_seconds()


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


p_first, p_last = get_first_and_last_loss_index(pcap_df)

rate = get_policing_rate(pcap_df, p_first, p_last)
print(f"Goodput: {rate}B/s")


t_used = 0
t_available = 0
lost_list = []
passed_list = []
# between the first and last lost packet, all packets used tokens
for i in range(p_first + 1, p_last):
    p_current = pcap_df.iloc[i]
    t_produced = rate * \
        (p_current['timestamp'] - pcap_df.iloc[p_first]
         ['timestamp']).total_seconds()
    t_available = t_produced - t_used
    if p_current['is_lost']:
        lost_list.append(t_available)
    else:
        passed_list.append(t_available)
        t_used += p_current['pkt_len']

print(f"avaiable size at the end: {t_available}B")
print(f"used total bytes at the end: {t_used}B")

was_policing_happening(lost_list, passed_list)
