import pandas as pd

def compute_policing_rate_avg_tx(df):
    throughputs = []
    sum_delivered = 0
    last_loss_time = 0
    for idx, row in df.iterrows():
        if not row['is_lost']:
            sum_delivered += row['pkt_len']
        else:
            throughputs.append(sum_delivered / (row['timestamp'] - last_loss_time))
            last_loss_time = row['timestamp']
            sum_delivered = 0
    
    throughputs.append(sum_delivered / (df.iloc[-1]['timestamp'] - last_loss_time))
    # print("total sum delivered: ", sum_delivered)
    # print("average received packet size: ", sum_delivered / counter)
    print("tx count: ", len(throughputs))
    if len(throughputs) == 0:
        return 0
    return sum(throughputs) / len(throughputs) * 8 # convert to bps

def compute_policing_rate_tx_samples(client: pd.DataFrame, sample_time: float = 0.01):
    throughputs = []
    sum_delivered = 0
    last_time = 0
    next_time = sample_time
    for idx, row in client.iterrows():
        if last_time <= row['timestamp'] < next_time:
            sum_delivered += row['length']
        else:
            # if sum_delivered > 0:
            last_time = next_time
            next_time += sample_time
            throughputs.append(sum_delivered / sample_time)
            sum_delivered = row['length']
    throughputs.append(sum_delivered / sample_time)
    print("tx count: ", len(throughputs))
    if len(throughputs) == 0:
        return 0
    return sum(throughputs) / len(throughputs) * 8 # convert to bps

def compute_policing_rate_cumulative_df(client: pd.DataFrame, filter: float = 0.0006):
    client = client.sort_values(by='time').reset_index(drop=True)
    client['cum_size'] = client['length'].cumsum()
    client['cum_size'] = client['cum_size']
    # rtt = run.get_rtt_on_client()
    # print("initial RTT:", rtt)
    
    client['gap_time'] = client['time'].diff().fillna(0)
    client['rate_b_per_s'] = client['cum_size'].diff() / client['gap_time']
    client['rate_b_per_s'] = client['rate_b_per_s'].fillna(0)
    
    res = client[client['gap_time'] >= filter]
    return res['rate_b_per_s'].mean() if not res.empty else 0


def compute_using_cwnd(merged_df, time_barrier = 1):
    merged_df['throughput'] = merged_df['cwnd'] / merged_df['delay']
    merged_df['throughput'] = merged_df['throughput'] * 8 / 1e6

    merged_df = merged_df.rename(columns={'delay': 'metric', 'used': 'source'})
    
    merged_df = merged_df[merged_df['time'] > time_barrier]
    
    return merged_df['throughput'].mean()