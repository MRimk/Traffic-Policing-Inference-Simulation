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

#include "complex-send-app.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/random-variable-stream.h"
#include "ns3/tcp-header.h"
#include "ns3/traffic-control-module.h"
#include "utils.h"

#include <fstream> // store throughput data
#include <string>
#include <vector>

// This simple example shows how to use TrafficControlHelper to install a
// QueueDisc on a device.
//
// Network topology
//
// n4 -----|                   |----- n5
//         |                   |
// n0 -----n3 (Queue X) ------ n6 ------n1 (TBF)----- n2
//    point-to-point links
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

static uint32_t g_ipTxCount = 0;
static uint32_t g_ipRxCount = 0;
static uint32_t g_ipRxTotal = 0;

static uint32_t sumRxBytes = 0;
static double t_firstLoss = -1.0;
static double t_lastLoss = -1.0;

static const uint32_t MIN_SEND_RATE = 1;
static const uint32_t MAX_SEND_RATE = 1448;

static const std::string SIM_NAME = "xtopo";

static uint16_t testPort = 7;
static uint16_t backgroundPort = 8;

static std::vector<uint32_t> sums;

static void Ipv4TxTrace(Ptr<const Packet> packet, Ptr<Ipv4> ipv4,
                        uint32_t interface) {
  // Called whenever IP sends down a packet (before qdisc)
  g_ipTxCount++;
}

static void Ipv4RxTrace(Ptr<const Packet> packet, Ptr<Ipv4> ipv4,
                        uint32_t interface) {
  // Called whenever IP receives a packet (after it’s demuxed up from L2)
  // std::cout << "received: " << packet->GetSize() << std::endl;
  g_ipRxCount++;
  g_ipRxTotal += packet->GetSize();
  if (t_firstLoss > 0)
    sumRxBytes += packet->GetSize();
}

std::ofstream droppedPacketsFile("wehe-dropped-packets.txt");

void PacketDropCallback(Ptr<const QueueDiscItem> item) {
  double dropSeconds = Simulator::Now().GetSeconds();

  if (t_firstLoss < 0)
    t_firstLoss = dropSeconds;
  t_lastLoss = dropSeconds;
  sums.push_back(sumRxBytes);

  TcpHeader tcpHeader;
  Ptr<const Packet> packet = item->GetPacket();
  if (packet->PeekHeader(tcpHeader))
    droppedPacketsFile << dropSeconds << ","
                       << tcpHeader.GetSequenceNumber().GetValue() << ","
                       << packet->GetSize() << std::endl;
  else
    droppedPacketsFile << dropSeconds << ",," << packet->GetSize() << std::endl;
}

int main(int argc, char *argv[]) {
  //   LogComponentEnable("TbfExample", LOG_LEVEL_INFO);
  //   LogComponentEnable("ComplexSendApplication", LOG_LEVEL_DEBUG);

  double simulationTime = 11.1; // seconds
  double simStart = 0.1;
  double simEnd = simulationTime - 1;

  uint32_t payloadSize = 1448; // bytes
  uint32_t burst = 500000;
  uint32_t mtu = 0; // second bucket is disabled
  DataRate rate = DataRate("2Mbps");
  DataRate peakRate = DataRate("0bps");

  std::string queueSize = "1p";

  CommandLine cmd(__FILE__);
  cmd.AddValue("burst", "Size of first bucket in bytes", burst);
  cmd.AddValue("mtu", "Size of second bucket in bytes", mtu);
  cmd.AddValue("rate", "Rate of tokens arriving in first bucket", rate);
  cmd.AddValue("peakRate", "Rate of tokens arriving in second bucket",
               peakRate);
  cmd.AddValue("queueSize",
               "Amount of bytes or packets that can be stored in the bucket "
               "instead of dropping the packet. Queue size in bytes or packets",
               queueSize);

  cmd.Parse(argc, argv);

  NodeContainer nodes;
  nodes.Create(7);

  PointToPointHelper pointToPoint_s_0;
  pointToPoint_s_0.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_s_0.SetChannelAttribute("Delay", StringValue("5ms"));

  PointToPointHelper pointToPoint_s_1;
  pointToPoint_s_1.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_s_1.SetChannelAttribute("Delay", StringValue("5ms"));

  PointToPointHelper pointToPoint_s_2;
  pointToPoint_s_2.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_s_2.SetChannelAttribute(
      "Delay", StringValue("0ms")); // no delay between X queue and TBF

  PointToPointHelper pointToPoint_s_3;
  pointToPoint_s_3.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_s_3.SetChannelAttribute("Delay", StringValue("5ms"));

  PointToPointHelper pointToPoint_b_0;
  pointToPoint_b_0.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_b_0.SetChannelAttribute("Delay", StringValue("5ms"));

  PointToPointHelper pointToPoint_b_1;
  pointToPoint_b_1.SetDeviceAttribute("DataRate",
                                      StringValue("20Mb/s")); // link bandwidth
  pointToPoint_b_1.SetChannelAttribute("Delay", StringValue("5ms"));

  // ORIGINAL LAYOUT
  // Test server -> X queue
  NetDeviceContainer devices_s_0 =
      pointToPoint_s_0.Install(nodes.Get(0), nodes.Get(3));
  // Original link: TBF -> receiver
  NetDeviceContainer devices_s_1 =
      pointToPoint_s_1.Install(nodes.Get(1), nodes.Get(2));

  // ADDED LAYOUT
  // X queue -> helper node
  NetDeviceContainer devices_s_2 =
      pointToPoint_s_3.Install(nodes.Get(3), nodes.Get(6));

  // helper node -> TBF
  NetDeviceContainer devices_s_3 =
      pointToPoint_s_2.Install(nodes.Get(6), nodes.Get(1));

  // Background server -> X queue
  NetDeviceContainer devices_b_0 =
      pointToPoint_b_0.Install(nodes.Get(4), nodes.Get(3));

  // helper node -> background receiver
  NetDeviceContainer devices_b_1 =
      pointToPoint_b_1.Install(nodes.Get(6), nodes.Get(5));

  InternetStackHelper stack;
  stack.Install(nodes);

  // =========================== TBF QueueDisc ==========================
  TrafficControlHelper tch;
  tch.SetRootQueueDisc("ns3::TbfQueueDisc", "MaxSize",
                       QueueSizeValue(QueueSize(queueSize)), "Burst",
                       UintegerValue(burst), "Mtu", UintegerValue(mtu), "Rate",
                       DataRateValue(DataRate(rate)), "PeakRate",
                       DataRateValue(DataRate(peakRate)));
  QueueDiscContainer qdiscs = tch.Install(devices_s_3.Get(0));
  Ptr<QueueDisc> q = qdiscs.Get(0);
  q->TraceConnectWithoutContext("Drop", MakeCallback(&PacketDropCallback));

  // =========================== X Queue ==========================
  std::string queueSizeX = "100p";
  DataRate rateX = DataRate("20Mbps"); // keep it one link speed
  uint32_t burstX = 500000;

  // TODO: burst should be constant
  TrafficControlHelper tch_x;
  tch_x.SetRootQueueDisc("ns3::TbfQueueDisc", "MaxSize",
                         QueueSizeValue(QueueSize(queueSizeX)), "Burst",
                         UintegerValue(burstX), "Mtu", UintegerValue(mtu),
                         "Rate", DataRateValue(DataRate(rateX)), "PeakRate",
                         DataRateValue(DataRate(peakRate)));
  QueueDiscContainer qdiscs_x = tch_x.Install(devices_s_2.Get(0));
  // Ptr<QueueDisc> q = qdiscs.Get(0);
  // q->TraceConnectWithoutContext("Drop", MakeCallback(&PacketDropCallback));

  // Assign IP addresses:

  //   10.1.1.x on n0 <-> n3 (Test server -> X queue)
  //   10.1.2.x on n1 <-> n2 (Original link: TBF -> receiver)

  //   10.1.3.x on n3 <-> n6 (X queue -> helper node)
  //   10.1.6.x on n6 <-> n1 (helper node -> TBF)

  //   10.1.4.x on n4 <-> n3 (Background server -> X queue)
  //   10.1.5.x on n3 <-> n5 (X queue -> background receiver)

  Ipv4AddressHelper address_s_0, address_s_1, address_s_2, address_s_3, address_b_0,
      address_b_1;
  address_s_0.SetBase("10.1.1.0", "255.255.255.0");
  address_s_1.SetBase("10.1.2.0", "255.255.255.0");
  address_s_2.SetBase("10.1.3.0", "255.255.255.0");
  address_s_3.SetBase("10.1.6.0", "255.255.255.0");
  address_b_0.SetBase("10.1.4.0", "255.255.255.0");
  address_b_1.SetBase("10.1.5.0", "255.255.255.0");

  Ipv4InterfaceContainer ifaces_s_0 = address_s_0.Assign(devices_s_0);
  Ipv4InterfaceContainer ifaces_s_1 = address_s_1.Assign(devices_s_1);
  Ipv4InterfaceContainer ifaces_s_2 = address_s_2.Assign(devices_s_2);
  Ipv4InterfaceContainer ifaces_s_3 = address_s_3.Assign(devices_s_3);
  Ipv4InterfaceContainer ifaces_b_0 = address_b_0.Assign(devices_b_0);
  Ipv4InterfaceContainer ifaces_b_1 = address_b_1.Assign(devices_b_1);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables();

  Ptr<Ipv4> ipv4_sender = nodes.Get(1)->GetObject<Ipv4>();
  Ptr<Ipv4> ipv4_dest = nodes.Get(2)->GetObject<Ipv4>();
  // “Tx” will fire when IP sends a packet down to the traffic-control layer
  ipv4_sender->TraceConnectWithoutContext("Tx", MakeCallback(&Ipv4TxTrace));

  // “Rx” will fire when IP receives a packet from the traffic-control layer
  ipv4_dest->TraceConnectWithoutContext("Rx", MakeCallback(&Ipv4RxTrace));

  // flow 1 on port1

  Address localAddress1(InetSocketAddress(Ipv4Address::GetAny(), testPort));
  PacketSinkHelper packetSinkHelper1("ns3::TcpSocketFactory", localAddress1);
  ApplicationContainer sinkApp1 = packetSinkHelper1.Install(nodes.Get(2));
  sinkApp1.Start(Seconds(0.0));
  sinkApp1.Stop(Seconds(simulationTime));

  // flow 2 on port2
  Address localAddress2(
      InetSocketAddress(Ipv4Address::GetAny(), backgroundPort));
  PacketSinkHelper packetSinkHelper2("ns3::TcpSocketFactory", localAddress2);
  ApplicationContainer sinkApp2 = packetSinkHelper2.Install(nodes.Get(5));
  sinkApp2.Start(Seconds(0.0));
  sinkApp2.Stop(Seconds(simulationTime));

  // sender 1
  Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(payloadSize));

  Ptr<ComplexSendApplication> app = CreateObject<ComplexSendApplication>();

  app->SetAttribute("Remote", AddressValue(InetSocketAddress(
                                  ifaces_s_1.GetAddress(1), testPort)));
  app->SetAttribute("MaxBytes", UintegerValue(0)); // 0 means send indefinitely
  app->SetAttribute("MinSend", UintegerValue(MIN_SEND_RATE));
  app->SetAttribute("MaxSend", UintegerValue(MAX_SEND_RATE));
  // app->SetAttribute ("EndTime", TimeValue (Seconds (simEnd)));  // set the
  // stop time

  nodes.Get(0)->AddApplication(app);
  app->SetStartTime(Seconds(simStart));
  app->SetStopTime(Seconds(simEnd));

  // sender 2
  // TODO: background should be random sized or constant sized?
  BulkSendHelper bulkSend2(
      "ns3::TcpSocketFactory",
      InetSocketAddress(ifaces_b_1.GetAddress(1), backgroundPort));
  bulkSend2.SetAttribute("MaxBytes", UintegerValue(0));
  bulkSend2.SetAttribute("SendSize", UintegerValue(payloadSize));

  ApplicationContainer apps2 = bulkSend2.Install(nodes.Get(4));
  apps2.Start(Seconds(simStart));
  apps2.Stop(Seconds(simEnd));

  std::vector<std::string> args;
  args.push_back(std::to_string(burst));
  args.push_back(queueSize);
  assignFiles(pointToPoint_s_0, pointToPoint_s_1, SIM_NAME, args);

  Simulator::Stop(Seconds(simulationTime + 5));
  Simulator::Run();

  Simulator::Destroy();

  double totalBytesReceived = g_ipRxTotal; // Get total received bytes
  double throughput =
      (totalBytesReceived * 8) / simulationTime; // Convert to bits per second

  std::cout << std::endl << "*** Throughput Statistics ***" << std::endl;
  std::cout << "Total Bytes Received: " << totalBytesReceived << " bytes"
            << std::endl;
  std::cout << "Throughput: " << throughput / 1e6 << " Mbps" << std::endl;

  droppedPacketsFile.close();

  std::ofstream metadata(getMetadataFileName(SIM_NAME, args));
  metadata << throughput << std::endl;  // Log throughput in bps
  metadata << sums.size() << std::endl; // Log number of dropped packets
  metadata.close();

  std::cout << std::endl << "*** TC Layer statistics ***" << std::endl;
  std::cout << q->GetStats() << std::endl;

  std::cout << "IP-layer Tx Count (before queue disc): " << g_ipTxCount
            << std::endl;
  std::cout << "IP-layer Rx Count (after queue disc):  " << g_ipRxCount
            << std::endl;

  if (!sums.empty()) {
    std::cout << std::endl << "*** Google paper estimation ***" << std::endl;
    std::cout << "Time between first and last loss: "
              << t_lastLoss - t_firstLoss << std::endl;
    std::cout << "The number of sums: " << sums.size() << std::endl;
    std::cout << "Bytes received in between first and last loss: "
              << sums[sums.size() - 1] << std::endl;
    std::cout << "Estimated goodput: "
              << sums[sums.size() - 1] / (t_lastLoss - t_firstLoss)
              << " B/s\t -> "
              << sums[sums.size() - 1] / (t_lastLoss - t_firstLoss) * 8
              << " b/s" << std::endl;
  }
  return 0;
}
