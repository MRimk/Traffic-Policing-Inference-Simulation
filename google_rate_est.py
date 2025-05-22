import pandas as pd

   
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
