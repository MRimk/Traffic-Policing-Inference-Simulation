# Traffic-Policing-Inference-Simulation
This project runs has simulation files to infer traffic policing rates. Part of broader WeHeY project at EPFL NAL lab

It uses ns-3 to simulate traffic and python to analyse the data

## Idea

Traffic differentiation (TD) is when Internet Service Providers (ISPs) apply different traffic management techniques to incoming traffic based on its source and/or content. ISPs may prioritize certain traffic by routing it through faster, dedicated paths, or throttle it using shapers and policers. These practices can be employed with good intentions—such as preventing video traffic from congesting the network—or to serve business needs.

However, users who suspect their traffic is being policed, or who confirm policing via the Wehe application, may wish to fully utilize the available throttled rate. Approaches like configuring the TCP receive window, tuning congestion control algorithms, or coordinating sender rates can help achieve maximum capacity. In this project, we instead focus on inferring the bottleneck rate from recorded network traffic flows.

Our goal is to assess the accuracy and reliability of existing policing rate estimation methods and to develop new ones. We examine both sender-side and receiver-side estimation, highlighting the advantages of knowing the bottleneck rate at each end. For both perspectives, we analyze how varying token bucket parameters—maintaining a constant rate while altering burst length and policer queue size—impacts estimation accuracy. Additionally, we evaluate two network topologies: a simple sender–receiver setup and a cross-traffic topology with background load.


## Usage

### Running the experiments

1. Move the ns3 simulation file containing `main()` into main directory out of its subfolder
2. Run `python run_sim.py --command [insert command name]`. Available commands: \[`shaping`, `complex-shaping`, `xtopo`\]. User can add `--reno` flag to indicate that TCP NewReno should be used for the experiments.
3. Compute traffic differentiation estimation using either all methods:
- Use `sh run_all_comp.sh` for all methods and all experiments, 
- Or for each method`python google-paper-rate-estimation.py --command [same command as before] --estimation [estimation method]`. Estimation methods are: \[ `GOOGLE`, `TX_GAPS`, `TX_SAMPLE`, `CUMULATIVE`, `CWND`\].
4. Use results csv files to visualize the results in `note_analyse_results.ipynb` notebook. Results are stored in `data/results_[command]_[estimation].csv`

