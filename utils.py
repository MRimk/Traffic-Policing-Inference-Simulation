from io import StringIO
import math
import subprocess

import pandas as pd
import numpy as np


def pcap_to_df(pcap_path, fields, pkt_filter=None):
    command = ['tshark', '-r', pcap_path, '-T', 'fields',
               '-E', 'header=y', '-E', 'separator=,', '-E', 'quote=d']
    for f in fields:
        command += ['-e', f]
    if pkt_filter:
        command += ['-Y', pkt_filter]

    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output, err = p.communicate()

    return pd.read_csv(StringIO(output.decode('utf-8')))


def find_last_not_retransmission(df, current_index):
    current_position = df.index.get_loc(current_index)
    for pos in range(current_position - 1, -1, -1):
        candidate = df.iloc[pos]
        if candidate['is_retransmission'] == 0:
            return candidate
    return df.iloc[0]


def get_hashes(df):
    df['hash'] = df.apply(
        # lambda row: hash((row['srcport'], row['dstport'], row['seq'], row['payload'])), # , row['is_retransmission']
        lambda row: hash((row['srcport'], row['dstport'], row['seq'])), # , row['is_retransmission']
        axis=1
    )
    return df

def get_lossEvents_from_hashes(server_pcap, client_pcap, server_port, real_lost=pd.DataFrame()):
    fields = {
        'frame.time_relative': 'time', 'tcp.seq': 'seq', 'tcp.len': 'length',
        'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
        'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
        'tcp.analysis.lost_segment': 'lost_segment',
        'tcp.nxtseq': 'next_seq',
        'tcp.ack': 'ack', 'tcp.payload': 'payload'
    }
    
    pkt_filter = "tcp.srcport=={}".format(server_port)
    
    server_df = pcap_to_df(server_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
    server_df['is_lost'] = False
    server_df['is_retransmission'] = server_df['is_retransmission'].fillna(0)
    server_df['lost_segment'] = server_df['lost_segment'].fillna(0)
    server_df = get_hashes(server_df)
    
    client_df = pcap_to_df(client_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
    # client_df = assign_ordered_packet_ids(client_df)
    client_df['is_retransmission'] = client_df['is_retransmission'].fillna(0)
    client_df['lost_segment'] = client_df['lost_segment'].fillna(0)
    client_df  = get_hashes(client_df)
   
    if real_lost.empty:
        server_df['is_lost'] = ~server_df['hash'].isin(client_df['hash'])
    else:
        server_df['is_lost'] = (server_df['seq'].isin(real_lost['seq'])) & (server_df['is_retransmission'] != 1)
    
    print("server lost data: ", server_df[server_df['is_lost'] == True].shape)
    return pd.DataFrame({'timestamp': server_df.time, 'pkt_len': server_df.length, 'is_lost': server_df.is_lost})
 

def get_lossEvents_from_lost_segments(server_pcap, client_pcap, server_port):
    fields = {
        'frame.time_relative': 'time', 'tcp.seq': 'seq', 'tcp.len': 'length',
        'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
        'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
        'tcp.analysis.lost_segment': 'lost_segment',
        'tcp.nxtseq': 'next_seq',
        'tcp.ack': 'ack'
    }
    
    pkt_filter = "tcp.srcport=={}".format(server_port)
    
    server_df = pcap_to_df(server_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
    server_df['is_lost'] = False
    server_df['lost_segment'] = server_df['lost_segment'].fillna(0)
    server_df['is_retransmission'] = server_df['is_retransmission'].fillna(0)
    
    fake_packets = []  # List to collect fake packet rows.
    lost_sizes = []

    for i, row in server_df.iterrows():
        if row['lost_segment'] == 1:
            # Get the previous non-retransmission packet.
            prev_packet = find_last_not_retransmission(server_df, i)
            lost_size = row['seq'] - prev_packet['next_seq']
            lost_sizes.append(lost_size)
            
            # fake packet as timestamp only matters
            fake_packet = row.copy()
            fake_packet['time'] = row['time'] - 0.001
            fake_packet['is_lost'] = True
            fake_packets.append(fake_packet)

    # Append the fake packet rows to df_copy.
    if fake_packets:
        fake_df = pd.DataFrame(fake_packets)
        server_df = pd.concat([server_df, fake_df], ignore_index=True)

    server_df.sort_values(by='time', inplace=True) 
    
        
    lost_packets = [size / 1448 for size in lost_sizes]
    print("lost packets: ", lost_packets)
    print("total: ", sum(lost_packets))
    return pd.DataFrame({'timestamp': server_df.time, 'pkt_len': server_df.length, 'is_lost': server_df.is_lost})
    

# pcap files:
# seq num of receiver -> out of order or duplicate ack issued -> loss
# we don't care if the same packet is dropped because we treat it as a lost packet
# id seq time           id seq time
# 0    1    0:0          0   1    0:0 <- delivered
#  1   2    0:1(is lost) 
#  2   2    0:2(is_retransmitted)        
#  3   3    0:3          1   3    0:3
#                        2   2    0:4 (out_of_order)

# not to do: from digest we will now how many packets were dropped but not what was dropped


def assign_ordered_packet_ids(df):
    current_id = 0
    max_seq = -1
    ids = []

    for _, row in df.iterrows():
        seq = row['seq']
        
        if row['is_out_of_order']:
            current_id += seq - max_seq - 1
        
        max_seq = max(seq, max_seq)        
        ids.append(current_id)        
        current_id += 1

    df['id'] = ids
    return df

def assign_all_packet_ids(df):
    df['id'] = range(0, df.shape[0])
    return df


def are_packets_acked(df, server_port):
    df = df.sort_values('time').reset_index(drop=True)

    df['ack_received'] = False
    
    for i, row in df.iterrows():
        # non-zero length and only packets that are sent from server
        if row['length'] == 0 or row['srcport'] == server_port:
            continue
        
        expected_ack = row['seq'] + row['length']
        
        # Find packets that:
        # - Occur later than the current packet (time > row['time'])
        # - Are sent from the destination back to the source
        # - Have an ack number at least equal to the expected ack
        ack_packets = df[
            (df['time'] > row['time']) &
            (df['srcport'] == row['dstport']) &
            (df['dstport'] == row['srcport']) &
            (df['ack'] >= expected_ack)
        ]
        
        # If any such ack packets are found, mark this packet as acknowledged
        if not ack_packets.empty:
            df.at[i, 'ack_received'] = True
    return df


def assign_loss(group, ack_time):
    # If the group has only one record, return False for that record.
    if len(group) == 1:
        group['is_lost'] = False
    else:
        time = ack_time
        relative_time = math.inf
        for item in group:
            diff = ack_time - item['time'] 
            if diff > 0 and diff < relative_time:
               relative_time = diff
               time = item['time'] 
        group['is_lost'] = group["time"] == time
    return group


def preprocess_df(df):
    df['is_lost'] = False
    df['is_retransmission'] = df['is_retransmission'].fillna(0)
    df = get_hashes(df)
    
    df = df[df['tcp_length'] > 0] # so that we ignore SYN packets with 0 payload
    
    return df


def get_lossEvents_from_server_client_pcaps(server_pcap, client_pcap, server_port):
    fields = {
        'frame.time_relative': 'time', 'tcp.seq': 'seq', 'ip.len': 'length', 'tcp.len': 'tcp_length',
        'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
        'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
        'tcp.ack': 'ack'
    }
    
    pkt_filter = "tcp.srcport=={}".format(server_port)
    
    server_df = pcap_to_df(server_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
    server_df = preprocess_df(server_df)
    
    client_df = pcap_to_df(client_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
    client_df = preprocess_df(client_df)    
    
    # reset indexing, becaues we filtered by length
    server_df = server_df.reset_index(drop=True)    
    
    # Default case: server packet hash does not exist in client side hashes:
    server_df['is_lost'] = ~server_df['hash'].isin(client_df['hash'])

    # Case where client has received packet, but there could be several transmissions of it:
    for _, client_row in client_df.iterrows():
        current_hash = client_row['hash']
        received_time = client_row['time']
        
        # get all packets that were sent and have the same hash
        sent_subset = server_df[server_df['hash'] == current_hash]
        
        # Check if there are multiple matching rows, as one is just delivered
        if len(sent_subset) > 1:
            # edge case where we don't find any of the packets that have time lower than received, so we don't know what's up with them
            # For now: they are marked as not lost
            sent_before = sent_subset[sent_subset['time'] < received_time]      
            
            if not sent_before.empty:
                # set all associated packets that were sent before arrival as lost
                for idx, row in sent_before.iterrows():    
                    server_df.loc[idx, 'is_lost'] = True
                
                # Find the index of the row with the closest timestamp to arrival among the valid ones, and mark it as not lost
                idx_closest = sent_before['time'].idxmax()
                server_df.loc[idx_closest, 'is_lost'] = False

    print("server lost events shape: ", server_df[server_df['is_lost'] == True].shape)
            
    return pd.DataFrame({'timestamp': server_df.time, 'pkt_len': server_df.length, 'seq': server_df.seq, 'is_lost': server_df.is_lost})
    
    

def get_lossEvents_from_pcap(pcap_file, server_port):
    # get the pkts sent by the server
    # print("getting loss events from pcap")
    fields = {
        'frame.time_relative': 'time', 'tcp.seq': 'seq', 'tcp.len': 'length',
        'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
        'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
    }
    pkt_filter = "tcp.srcport=={}".format(server_port)
    pkts_df = pcap_to_df(pcap_file, fields.keys(),
                         pkt_filter=pkt_filter).rename(columns=fields)

    pkts_df['is_lost'] = False
    pkts_df['next_seq'] = pkts_df['seq'] + pkts_df['length']

    # find retransmitted packets
    # print("pkts_df shape", pkts_df.shape)

    retransmitted_pkts = pkts_df[(pkts_df.is_retransmission == 1) | (pkts_df.is_out_of_order == 1)].drop_duplicates(
        subset='seq', keep="last")
    # print(retransmitted_pkts)
    # print("retransmitted pkts shape", retransmitted_pkts.shape)

    # find packets that were re-transmitted and compute non/lost bytes sum
    lost_pkts = pd.merge(pkts_df, retransmitted_pkts, how='cross')
    # print("merged pkts df and retransmitted shape", lost_pkts.shape)
    print(lost_pkts.columns)

    lost_pkts = lost_pkts[
        (lost_pkts['seq_y'] >= lost_pkts['seq_x']) &
        (lost_pkts['seq_y'] < lost_pkts['next_seq_x']) &
        (lost_pkts['time_x'] < lost_pkts['time_y'])]
    
    # print("lost pckts:", lost_pkts)
    lost_pkts = lost_pkts.drop_duplicates(subset='time_y', keep="last")
    # print("lost pkts after dropping duplicates", lost_pkts.shape)
    lost_pkts = lost_pkts.groupby(['time_x', 'seq_x']).apply(
        compute_loss_vs_nonloss_sum).reset_index(name='loss')
    lost_pkts[['loss_sum', 'nonloss_sum']] = lost_pkts['loss'].apply(pd.Series)
    # print("after grouping and loss sums", lost_pkts.shape)

    labeled_sent_pkts = pd.concat([
        pd.DataFrame({'time': lost_pkts['time_x'], 'seq': lost_pkts['seq_x'],
                     'length': lost_pkts['loss_sum'], 'is_lost': True}),
        pd.DataFrame({'time': lost_pkts['time_x'], 'seq': lost_pkts['seq_x'],
                     'length': lost_pkts['nonloss_sum'], 'is_lost': False})
    ])

    # label loss in the original sent_pkts dataframe
    pkts_df = pd.merge(pkts_df, labeled_sent_pkts,
                       how='outer', on=['time', 'seq'])
    pkts_df['is_lost'] = pkts_df['is_lost_y'].fillna(
        False) & pkts_df['is_lost_y']
    pkts_df['length_y'] = pkts_df['length_y'].fillna(1e10)
    pkts_df['length'] = pkts_df[['length_x', 'length_y']].min(axis=1)

    return pd.DataFrame({'timestamp': pkts_df.time, 'pkt_len': pkts_df.length, 'is_lost': pkts_df.is_lost})


def compute_loss_vs_nonloss_sum(vals):
    total_sum, loss_sum = vals['length_x'].iat[0], vals['length_y'].sum()
    return loss_sum, total_sum - loss_sum


def generate_random_loss_df(seed=42, num_packets=1500, loss_prob=0.2):
    # Set random seed for reproducibility
    np.random.seed(seed)

    # Generate random timestamps
    timestamps = pd.date_range(
        start="2024-01-01", periods=num_packets, freq="min")

    # Generate random packet lengths between 50 and 1500 bytes
    pkt_lengths = np.random.randint(50, 1500, size=num_packets)

    is_lost = np.random.choice([True, False], size=num_packets, p=[
                               loss_prob, 1-loss_prob])

    return pd.DataFrame({'timestamp': timestamps, 'pkt_len': pkt_lengths, 'is_lost': is_lost})
