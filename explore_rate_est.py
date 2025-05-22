import pandas as pd

def compute_policing_rate_avg_tx(df):
    throughputs = []
    sum_delivered = 0
    last_loss_time = 0
    for idx, row in df.iterrows():
        if not row['is_lost']:
            sum_delivered += row['pkt_len']
        else:
            # if sum_delivered > 0:
            throughputs.append(sum_delivered / (row['timestamp'] - last_loss_time))
            last_loss_time = row['timestamp']
            sum_delivered = 0
    
    if sum_delivered > 0:
        throughputs.append(sum_delivered / (df.iloc[-1]['timestamp'] - last_loss_time))
    # print("total sum delivered: ", sum_delivered)
    # print("average received packet size: ", sum_delivered / counter)
    print("tx count: ", len(throughputs))
    if len(throughputs) == 0:
        return 0
    return sum(throughputs) / len(throughputs) * 8 # convert to bps
