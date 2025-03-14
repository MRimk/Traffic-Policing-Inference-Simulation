from io import StringIO
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
    # print(lost_pkts.columns)

    lost_pkts = lost_pkts[
        (lost_pkts['seq_y'] >= lost_pkts['seq_x']) &
        (lost_pkts['seq_y'] < lost_pkts['next_seq_x']) &
        (lost_pkts['time_x'] < lost_pkts['time_y'])]
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
