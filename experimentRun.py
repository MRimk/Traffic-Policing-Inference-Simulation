import utils
import pandas
from google_rate_est import get_first_and_last_loss_index, get_policing_rate
from explore_rate_est import *
from enum import Enum

SERVER_PORT = 49153
CLIENT_PORT = 7

class RateEstimationMethod(Enum):
    GOOGLE = "google"
    TX_GAPS = "tx_gaps"
    TX_SAMPLE = "tx_sample"
    CUMULATIVE = "cumulative"
    CWND = "cwnd"

class ExperimentRun:
    def __init__(self, name, server_pcap, client_pcap, metadata_file, params, estimation=RateEstimationMethod.GOOGLE):
        self.name = name
        self.server_pcap = server_pcap
        self.client_pcap = client_pcap
        self.metadata_file = metadata_file
        self.params = params
        self.metadata = self.get_metadata_info()
        self.estimation = estimation
        
        self.field = {
            'frame.time_relative': 'time', 'tcp.seq': 'seq', 'ip.len': 'length', 'tcp.len': 'tcp_length',
            'tcp.srcport': 'srcport', 'tcp.dstport': 'dstport',
            'tcp.analysis.out_of_order': 'is_out_of_order', 'tcp.analysis.retransmission': 'is_retransmission',
            'tcp.ack': 'ack'
        }
        
        self.pkt_filter = "tcp.srcport=={}".format(SERVER_PORT)

    def get_pcap_df(self):
        return utils.get_lossEvents_from_server_client_pcaps(
            self.server_pcap, self.client_pcap, SERVER_PORT)
        
    def get_metadata_info(self):
        if not self.metadata_file:
            return [0.0, 0.0]
        with open(self.metadata_file, 'r') as f:
            lines = f.readlines()
            metadata = [float(lines[0]), int(lines[1])]
            return metadata
        
    def get_estimated_rate(self):
        rate = 0.0
        if self.estimation == RateEstimationMethod.TX_GAPS.name:
            rate = compute_policing_rate_avg_tx(self.get_pcap_df())
        elif self.estimation == RateEstimationMethod.GOOGLE.name:
            first, last = get_first_and_last_loss_index(self.get_pcap_df())
            rate = get_policing_rate(self.get_pcap_df(), first, last)
        elif self.estimation == RateEstimationMethod.TX_SAMPLE.name:
            rate = compute_policing_rate_tx_samples(self.get_client_df(), sample_time=0.01)
        elif self.estimation == RateEstimationMethod.CUMULATIVE.name:
            rate = compute_policing_rate_cumulative_df(self.get_client_df(), filter=0.00001)
        elif self.estimation == RateEstimationMethod.CWND.name:
            rate = compute_using_cwnd(self.get_cwnd_details(), time_barrier = 1)
        else:
            raise ValueError("Invalid estimation method")
        return rate
    
    def get_rtt_on_client(self):
        fields = {"tcp.analysis.initial_rtt": "rtt"}
        pkt_filter = "tcp.srcport=={}".format(CLIENT_PORT)
        client_df = utils.pcap_to_df(self.client_pcap, fields.keys(), pkt_filter=pkt_filter).rename(columns=fields)
        if client_df.empty:
            return 0.0
        rtt = client_df['rtt'].max()
        return rtt
    
    def get_client_df(self):
        client_df = utils.pcap_to_df(self.client_pcap, self.field.keys(), pkt_filter=self.pkt_filter).rename(columns=self.field)
        # client_df = preprocess_df(client_df)
        return client_df
        
    def get_client_rx_throughput(self):
        client_df = self.get_client_df()
        # client_df = preprocess_df(client_df)
        
        if client_df.empty:
            return 0
        data_rx = client_df['length'].sum() # ip.len
        first_packet_time = client_df['time'].iloc[0]
        last_packet_time = client_df['time'].iloc[-1]
        elapsed_time = last_packet_time - first_packet_time
        throughput = data_rx / elapsed_time * 8 # convert to bps
        return throughput
    
    
    def get_cwnd_details(self):
        if not self.metadata_file:
            raise ValueError("Metadata file is required to get cwnd details.")
        
        file_cwnd = self.metadata_file.replace("metadata", "cwnd")
        file_rtt = self.metadata_file.replace("metadata", "rtt")
        file_rto = self.metadata_file.replace("metadata", "rto")

        cwnd = pd.read_csv(file_cwnd, header=None, names=['time', 'cwnd'])
        rtt = pd.read_csv(file_rtt, header=None, names=['time', 'delay'])
        rtt['used'] = 'rtt'
        rto = pd.read_csv(file_rto, header=None, names=['time', 'delay'])
        rto['used'] = 'rto'

        delays = pd.concat([rtt, rto], ignore_index=True).sort_values('time')
        cwnd = cwnd.sort_values('time')
        merged = pd.merge_asof(cwnd, delays, on='time', direction='nearest')
        return merged
    
    def __repr__(self):
        return f"ExperimentRun(name={self.name}, server_pcap={self.server_pcap}, client_pcap={self.client_pcap}, metadata_file={self.metadata_file}, params={self.params})"
    

def is_correct_num_lost(df, expected_lost):
    return (( df[df['is_lost']== True].shape[0] - expected_lost) / expected_lost, (df[df['is_lost']== True].shape[0] - expected_lost) / expected_lost)

def is_correct_rate(rate, expected_rate):
    return ((rate - expected_rate) / expected_rate, abs(rate - expected_rate) / expected_rate)

def analyse_run(run: ExperimentRun):
    pcap_df = run.get_pcap_df()
    throughput = run.get_client_rx_throughput()
    print(f"Throughput at rx: {throughput}")
    num_lost = pcap_df[pcap_df['is_lost']== True].shape[0]
    error_lost, error_lost_abs = 0, 0
    if run.estimation == RateEstimationMethod.GOOGLE.name:
        if num_lost > 0 and run.metadata[1] == 0:
            print(f"FALSE POSITIVE: Lost packets detected ({num_lost})but no expected lost packets.")
        
        if num_lost < 15 or run.metadata[1] == 0:
            return {"burst": run.params[0], "queue_size": run.params[1], "rate": 0, "lost": num_lost, "error_lost": 0, "error_lost_abs": 0, "error_rate": 1, "error_rate_abs": 1, "actual_rate": run.metadata[0], "rx_rate": throughput}
 
        error_lost, error_lost_abs = is_correct_num_lost(pcap_df, run.metadata[1]) 
    
    try:
        rate = run.get_estimated_rate()
    except:
        return None
        
    if throughput == 0:
        error_rate = 1
        error_rate_abs = 1
    else:
        error_rate, error_rate_abs = is_correct_rate(rate, throughput)
        if abs(rate - run.metadata[0]) > 0:
            print(f"Rate error: {error_rate}, Rate: {rate}, Expected rate: {throughput}")
    
    return {"burst": run.params[0], "queue_size": run.params[1], "rate": rate, "lost": num_lost, "error_lost": error_lost, "error_lost_abs": error_lost_abs, "error_rate": error_rate, "error_rate_abs": error_rate_abs,"actual_rate": run.metadata[0], "rx_rate": throughput}
    
    