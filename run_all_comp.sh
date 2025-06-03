#!/bin/bash
SECONDS=0
python google-paper-rate-estimation.py --command complex-shaping --estimation TX_SAMPLE
echo $SECONDS
python google-paper-rate-estimation.py --command shaping --estimation TX_SAMPLE
echo $SECONDS
python google-paper-rate-estimation.py --command xtopo --estimation TX_SAMPLE
echo $SECONDS

python google-paper-rate-estimation.py --command complex-shaping --estimation CWND
echo $SECONDS
python google-paper-rate-estimation.py --command shaping --estimation CWND
echo $SECONDS
python google-paper-rate-estimation.py --command xtopo --estimation CWND
echo $SECONDS

python google-paper-rate-estimation.py --command complex-shaping --estimation GOOGLE
echo $SECONDS
python google-paper-rate-estimation.py --command shaping --estimation GOOGLE
echo $SECONDS
python google-paper-rate-estimation.py --command xtopo --estimation GOOGLE
echo $SECONDS

python google-paper-rate-estimation.py --command complex-shaping --estimation CUMULATIVE
echo $SECONDS
python google-paper-rate-estimation.py --command shaping --estimation CUMULATIVE
echo $SECONDS
python google-paper-rate-estimation.py --command xtopo --estimation CUMULATIVE
echo $SECONDS

python google-paper-rate-estimation.py --command complex-shaping --estimation TX_GAPS
echo $SECONDS
python google-paper-rate-estimation.py --command shaping --estimation TX_GAPS
echo $SECONDS
python google-paper-rate-estimation.py --command xtopo --estimation TX_GAPS
echo $SECONDS