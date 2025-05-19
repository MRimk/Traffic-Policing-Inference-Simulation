import types, sys, pickle, csv, pandas as pd #, ace_tools as tools

# ------- Load pickle with dummy module for unknown classes -------
class _Dummy:
    def __init__(self, *args, **kwargs):
        pass
    def __getattr__(self, name):
        # Nested unknown attribute => another dummy
        return _Dummy()
    def __setstate__(self, state):
        self.__dict__.update(state)
    def __getstate__(self):
        return self.__dict__

dummy_mod = types.ModuleType("python_lib")
dummy_mod.__getattr__ = lambda name: _Dummy
sys.modules["python_lib"] = dummy_mod

pickle_path = "send_data/Youtube_12122018.pcap_server_all.pickle"
with open(pickle_path, "rb") as f:
    data = pickle.load(f)

# ------- Extract (timestamp, order, size) triples -------
triples = []      # (timestamp, order, size)
order = 0
for proto_dict in data[0].values():  # server_data[0] holds {'udp':..., 'tcp':...}
    for pkt_list in proto_dict.values():
        for pkt in pkt_list:
            rl = getattr(pkt, "response_list", [])
            for resp in rl:
                payload = resp.payload
                if isinstance(payload, str):
                    size = len(payload) // 2  # hex string
                else:
                    size = len(payload)
                ts = resp.__dict__.get("timestamp", None)
                triples.append((ts if ts is not None else float("inf"), order, size))
                order += 1

# ------- Sort by timestamp then fallback to creation order -------
triples.sort(key=lambda t: (t[0], t[1]))

# ------- Export sequential sizes -------
csv_path = "send_data/youtube_packets.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["size"])
    for _, _, size in triples:
        writer.writerow([size])

# Show a preview (first 20 rows)
df_preview = pd.read_csv(csv_path, nrows=20)
# tools.display_dataframe_to_user(
#     "First 20 server packet sizes (chronological order)",
#     df_preview
# )

 