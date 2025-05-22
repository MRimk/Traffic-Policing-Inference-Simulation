import utils
import pandas
from google_rate_est import get_first_and_last_loss_index, get_policing_rate
from explore_rate_est import compute_policing_rate_avg_tx

SERVER_PORT = 49153

class ExperimentRun:
    def __init__(self, name, server_pcap, client_pcap, metadata_file, params, not_google_paper=False):
        self.name = name
        self.server_pcap = server_pcap
        self.client_pcap = client_pcap
        self.metadata_file = metadata_file
        self.params = params
        self.metadata = self.get_metadata_info()
        self.not_google_paper = not_google_paper
        
        self.field = fields = {
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
        if self.not_google_paper:
            rate = compute_policing_rate_avg_tx(self.get_pcap_df())
        else:
            first, last = get_first_and_last_loss_index(self.get_pcap_df())
            rate = get_policing_rate(self.get_pcap_df(), first, last)
        return rate
    
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
    if not run.not_google_paper:
        if num_lost > 0 and run.metadata[1] == 0:
            print(f"FALSE POSITIVE: Lost packets detected ({num_lost})but no expected lost packets.")
        
        if num_lost < 15 or run.metadata[1] == 0:
            return {"burst": run.params[0], "queue_size": run.params[1], "rate": 0, "lost": num_lost, "error_lost": 0, "error_lost_abs": 0, "error_rate": 1, "error_rate_abs": 1, "actual_rate": run.metadata[0], "rx_rate": throughput}
 
        error_lost, error_lost_abs = is_correct_num_lost(pcap_df, run.metadata[1]) 
    
    rate = run.get_estimated_rate()
    
    if throughput == 0:
        error_rate = 1
        error_rate_abs = 1
    else:
        error_rate, error_rate_abs = is_correct_rate(rate, throughput)
        if abs(rate - run.metadata[0]) > 0:
            print(f"Rate error: {error_rate}, Rate: {rate}, Expected rate: {throughput}")
    
    return {"burst": run.params[0], "queue_size": run.params[1], "rate": rate, "lost": num_lost, "error_lost": error_lost, "error_lost_abs": error_lost_abs, "error_rate": error_rate, "error_rate_abs": error_rate_abs,"actual_rate": run.metadata[0], "rx_rate": throughput}
    
    