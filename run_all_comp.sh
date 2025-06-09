#!/bin/bash
SECONDS=0
# echo "\n\n\n\n=======================START CWND======================\n"

# python google-paper-rate-estimation.py --command complex-shaping --estimation CWND
# python google-paper-rate-estimation.py --command shaping --estimation CWND

# echo "\n\n\n\n=======================START GOOGLE======================\n"
# python google-paper-rate-estimation.py --command complex-shaping --estimation GOOGLE
# python google-paper-rate-estimation.py --command shaping --estimation GOOGLE

# echo "\n\n\n\n=======================START CUMULATIVE======================\n"
# python google-paper-rate-estimation.py --command complex-shaping --estimation CUMULATIVE
# python google-paper-rate-estimation.py --command shaping --estimation CUMULATIVE

# echo "\n\n\n\n=======================START TX GAPS======================\n"
# python google-paper-rate-estimation.py --command complex-shaping --estimation TX_GAPS
# python google-paper-rate-estimation.py --command shaping --estimation TX_GAPS

# echo "\n\n\n\n=======================START TX SAMPLE======================\n"
# python google-paper-rate-estimation.py --command complex-shaping --estimation TX_SAMPLE
# python google-paper-rate-estimation.py --command shaping --estimation TX_SAMPLE


# echo "\n\n\n\n=======================START XTOPO CWND======================\n"
# python google-paper-rate-estimation.py --command xtopo --estimation CWND
# echo "\n\n\n\n=======================START XTOPO GOOGLE======================\n"
# python google-paper-rate-estimation.py --command xtopo --estimation GOOGLE
# echo "\n\n\n\n=======================START XTOPO CUMULATIVE======================\n"
# python google-paper-rate-estimation.py --command xtopo --estimation CUMULATIVE
# echo "\n\n\n\n=======================START XTOPO TX SAMPLE======================\n"
# python google-paper-rate-estimation.py --command xtopo --estimation TX_SAMPLE
# echo "\n\n\n\n=======================START XTOPO TX GAPS======================\n"
# python google-paper-rate-estimation.py --command xtopo --estimation TX_GAPS

echo "\n\n\n\n=======================START RENO CWND======================\n"
python google-paper-rate-estimation.py --command complex-shaping --estimation CWND --reno
python google-paper-rate-estimation.py --command xtopo --estimation CWND --reno
echo "\n\n\n\n=======================START RENO GOOGLE======================\n"
python google-paper-rate-estimation.py --command complex-shaping --estimation GOOGLE --reno
python google-paper-rate-estimation.py --command xtopo --estimation GOOGLE --reno
echo "\n\n\n\n=======================START RENO CUMULATIVE======================\n"
python google-paper-rate-estimation.py --command complex-shaping --estimation CUMULATIVE --reno
python google-paper-rate-estimation.py --command xtopo --estimation CUMULATIVE --reno
echo "\n\n\n\n=======================START RENO TX SAMPLE======================\n"
python google-paper-rate-estimation.py --command complex-shaping --estimation TX_SAMPLE --reno
python google-paper-rate-estimation.py --command xtopo --estimation TX_SAMPLE --reno
echo "\n\n\n\n=======================START RENO TX GAPS======================\n"
python google-paper-rate-estimation.py --command complex-shaping --estimation TX_GAPS --reno
python google-paper-rate-estimation.py --command xtopo --estimation TX_GAPS --reno
