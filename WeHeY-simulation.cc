/*
 * Copyright (c) 2015 Universita' degli Studi di Napoli "Federico II"
 *               2017 Kungliga Tekniska Högskolan
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Author: Pasquale Imputato <p.imputato@gmail.com>
 * Author: Stefano Avallone <stefano.avallone@unina.it>
 * Author: Surya Seetharaman <suryaseetharaman.9@gmail.com> - ported from ns-3
 *         RedQueueDisc traffic-control example to accommodate TbfQueueDisc
 * example.
 */

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <fstream> // store throughput data

// This simple example shows how to use TrafficControlHelper to install a
// QueueDisc on a device.
//
// Network topology
//
//       10.1.1.0
// n0 -------------- n1
//    point-to-point
//
// The output will consist of all the traced changes in
// the number of tokens in TBF's first and second buckets:
//
//    FirstBucketTokens 0 to x
//    SecondBucketTokens 0 to x
//    FirstBucketTokens x to 0
//    SecondBucketTokens x to 0
//

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("TbfExample");

void FirstBucketTokensTrace(uint32_t oldValue, uint32_t newValue) {
  std::cout << "FirstBucketTokens " << oldValue << " to " << newValue
            << std::endl;
}

void SecondBucketTokensTrace(uint32_t oldValue, uint32_t newValue) {
  std::cout << "SecondBucketTokens " << oldValue << " to " << newValue
            << std::endl;
}

std::ofstream throughputFile("wehe-throughput.txt");

void ThroughputMonitor(Ptr<PacketSink> sink, double interval) {
  double bytesReceived = sink->GetTotalRx(); // Get total received bytes
  static double lastBytes = 0;

  double throughput =
      ((bytesReceived - lastBytes) * 8) / interval; // Convert to bps
  lastBytes = bytesReceived;

  // Log time and throughput to file
  throughputFile << Simulator::Now().GetSeconds() << " " << throughput / 1e6
                 << std::endl;

  // Schedule next measurement
  Simulator::Schedule(Seconds(interval), &ThroughputMonitor, sink, interval);
}

int main(int argc, char *argv[]) {
  double simulationTime = 10;  // seconds
  uint32_t payloadSize = 1448; // bytes
  uint32_t burst = 500000;
  uint32_t mtu = 0; // second bucket is disabled
  DataRate rate = DataRate("2Mbps");
  DataRate peakRate = DataRate("0bps");

  CommandLine cmd(__FILE__);
  cmd.AddValue("burst", "Size of first bucket in bytes", burst);
  cmd.AddValue("mtu", "Size of second bucket in bytes", mtu);
  cmd.AddValue("rate", "Rate of tokens arriving in first bucket", rate);
  cmd.AddValue("peakRate", "Rate of tokens arriving in second bucket",
               peakRate);

  cmd.Parse(argc, argv);

  NodeContainer nodes;
  nodes.Create(2);

  PointToPointHelper pointToPoint;
  pointToPoint.SetDeviceAttribute("DataRate",
                                  StringValue("20Mb/s")); // link bandwidth
  pointToPoint.SetChannelAttribute("Delay", StringValue("0ms"));

  NetDeviceContainer devices;
  devices = pointToPoint.Install(nodes);

  InternetStackHelper stack;
  stack.Install(nodes);

  TrafficControlHelper tch;
  tch.SetRootQueueDisc("ns3::TbfQueueDisc", "Burst", UintegerValue(burst),
                       "Mtu", UintegerValue(mtu), "Rate",
                       DataRateValue(DataRate(rate)), "PeakRate",
                       DataRateValue(DataRate(peakRate)));
  QueueDiscContainer qdiscs = tch.Install(devices);

  Ptr<QueueDisc> q = qdiscs.Get(1);
  q->SetMaxSize(ns3::QueueSize(ns3::QueueSizeUnit::PACKETS, 1));
  q->TraceConnectWithoutContext("TokensInFirstBucket",
                                MakeCallback(&FirstBucketTokensTrace));
  q->TraceConnectWithoutContext("TokensInSecondBucket",
                                MakeCallback(&SecondBucketTokensTrace));

  Ipv4AddressHelper address;
  address.SetBase("10.1.1.0", "255.255.255.0");

  Ipv4InterfaceContainer interfaces = address.Assign(devices);

  // Flow
  uint16_t port = 7;
  Address localAddress(InetSocketAddress(Ipv4Address::GetAny(), port));
  PacketSinkHelper packetSinkHelper("ns3::TcpSocketFactory", localAddress);
  ApplicationContainer sinkApp = packetSinkHelper.Install(nodes.Get(0));

  sinkApp.Start(Seconds(0.0));
  sinkApp.Stop(Seconds(simulationTime + 0.1));

  Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(payloadSize));

  BulkSendHelper bulkSend("ns3::TcpSocketFactory",
                          InetSocketAddress(interfaces.GetAddress(0), port));
  bulkSend.SetAttribute("MaxBytes", UintegerValue(0));
  bulkSend.SetAttribute("SendSize", UintegerValue(payloadSize));

  apps.Add(bulkSend.Install(nodes.Get(1)));
  apps.Start(Seconds(0.0));
  apps.Stop(Seconds(simulationTime + 0.1));

  Ptr<PacketSink> sink = DynamicCast<PacketSink>(sinkApp.Get(0));
  double interval = 0.1; // Check throughput every 0.001 seconds
  Simulator::Schedule(Seconds(interval), &ThroughputMonitor, sink, interval);

  double totalBytesReceived = sink->GetTotalRx(); // Get total received bytes
  double throughput =
      (totalBytesReceived * 8) / simulationTime; // Convert to bits per second

  std::cout << std::endl << "*** Throughput Statistics ***" << std::endl;
  std::cout << "Total Bytes Received: " << totalBytesReceived << " bytes"
            << std::endl;
  std::cout << "Throughput: " << throughput / 1e6 << " Mbps" << std::endl;

  Simulator::Stop(Seconds(simulationTime + 5));
  Simulator::Run();

  Simulator::Destroy();

  throughputFile.close();

  std::cout << std::endl << "*** TC Layer statistics ***" << std::endl;
  std::cout << q->GetStats() << std::endl;
  return 0;
}