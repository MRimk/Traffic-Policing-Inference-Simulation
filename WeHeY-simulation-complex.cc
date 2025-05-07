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
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/random-variable-stream.h"
#include "ns3/tcp-header.h"
#include "ns3/traffic-control-module.h"
#include "utils.h"

#include <fstream> // store throughput data
#include <vector>

// This simple example shows how to use TrafficControlHelper to install a
// QueueDisc on a device.
//
// Network topology
//
//       10.1.1.0
// n0 ------n_TBF----- n1
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

static uint32_t g_ipTxCount = 0;
static uint32_t g_ipRxCount = 0;

static uint32_t sumRxBytes = 0;
static double t_firstLoss = -1.0;
static double t_lastLoss = -1.0;

static const uint32_t MIN_SEND_RATE = 0;
static const uint32_t MAX_SEND_RATE = 1400;

static std::vector<uint32_t> sums;

static void Ipv4TxTrace(Ptr<const Packet> packet, Ptr<Ipv4> ipv4,
                        uint32_t interface) {
  std::cout << "Tx packet size: " << packet->GetSize() << std::endl;

  g_ipTxCount++;
}

static void Ipv4RxTrace(Ptr<const Packet> packet, Ptr<Ipv4> ipv4,
                        uint32_t interface) {
  // Called whenever IP receives a packet (after it’s demuxed up from L2)
  g_ipRxCount++;
  if (packet->GetSize() < 1500)
    std::cout << "Rx small packet size: " << packet->GetSize() << std::endl;
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
  // std::cout << "Dropped packet size: " << packet->GetSize() << std::endl;
  if (packet->PeekHeader(tcpHeader))
    droppedPacketsFile << dropSeconds << ","
                       << tcpHeader.GetSequenceNumber().GetValue() << ","
                       << packet->GetSize() << std::endl;
  else
    droppedPacketsFile << dropSeconds << ",," << packet->GetSize() << std::endl;
}

// void RandomizeSendSize(Ptr<ComplexSendApplication> app,
//                        Ptr<UniformRandomVariable> var, double simulationEnd)
//                        {
//   if (Simulator::Now().GetSeconds() >= simulationEnd) {
//     std::cout << "simulation should end" << std::endl;
//     return;
//   }
//   uint32_t s = var->GetInteger(MIN_SEND_RATE, MAX_SEND_RATE);
//   app->SetAttribute("SendSize", UintegerValue(s));
//   // schedule again at the *very next* simulation tick,
//   // so BulkSendApplication::ScheduleTx() will see it
//   Simulator::ScheduleNow(Seconds(0.0001), &RandomizeSendSize, app, var,
//                          simulationEnd);
// }

int main(int argc, char *argv[]) {
  double simulationTime = 11.1; // seconds
  double simStart = 0.1;
  double simEnd = simulationTime - 1;

  uint32_t payloadSize = 1448; // bytes
  uint32_t burst = 500000;
  uint32_t mtu = 0; // second bucket is disabled
  DataRate rate = DataRate("2Mbps");
  DataRate peakRate = DataRate("0bps");

  Ptr<UniformRandomVariable> sizeVar = CreateObject<UniformRandomVariable>();

  CommandLine cmd(__FILE__);
  cmd.AddValue("burst", "Size of first bucket in bytes", burst);
  cmd.AddValue("mtu", "Size of second bucket in bytes", mtu);
  cmd.AddValue("rate", "Rate of tokens arriving in first bucket", rate);
  cmd.AddValue("peakRate", "Rate of tokens arriving in second bucket",
               peakRate);

  cmd.Parse(argc, argv);

  NodeContainer nodes;
  nodes.Create(3);

  PointToPointHelper pointToPoint1;
  pointToPoint1.SetDeviceAttribute("DataRate",
                                   StringValue("20Mb/s")); // link bandwidth
  pointToPoint1.SetChannelAttribute("Delay", StringValue("0ms"));

  PointToPointHelper pointToPoint2;
  pointToPoint2.SetDeviceAttribute("DataRate",
                                   StringValue("20Mb/s")); // link bandwidth
  pointToPoint2.SetChannelAttribute("Delay", StringValue("0ms"));

  NetDeviceContainer devices1 =
      pointToPoint1.Install(nodes.Get(0), nodes.Get(1));
  NetDeviceContainer devices2 =
      pointToPoint2.Install(nodes.Get(1), nodes.Get(2));

  InternetStackHelper stack;
  stack.Install(nodes);

  TrafficControlHelper tch;
  tch.SetRootQueueDisc("ns3::TbfQueueDisc", "MaxSize",
                       QueueSizeValue(QueueSize("1p")), "Burst",
                       UintegerValue(burst), "Mtu", UintegerValue(mtu), "Rate",
                       DataRateValue(DataRate(rate)), "PeakRate",
                       DataRateValue(DataRate(peakRate)));
  QueueDiscContainer qdiscs = tch.Install(devices2.Get(0));

  Ptr<QueueDisc> q = qdiscs.Get(0);
  q->SetMaxSize(ns3::QueueSize(ns3::QueueSizeUnit::PACKETS, 1));
  q->TraceConnectWithoutContext("Drop", MakeCallback(&PacketDropCallback));

  // Assign IP addresses:
  //   10.1.1.x on n0 <-> n1
  //   10.1.2.x on n1 <-> n2
  Ipv4AddressHelper address1, address2;
  address1.SetBase("10.1.1.0", "255.255.255.0");
  address2.SetBase("10.1.2.0", "255.255.255.0");

  Ipv4InterfaceContainer ifaces1 = address1.Assign(devices1);
  Ipv4InterfaceContainer ifaces2 = address2.Assign(devices2);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables();

  Ptr<Ipv4> ipv4_sender = nodes.Get(1)->GetObject<Ipv4>();
  Ptr<Ipv4> ipv4_dest = nodes.Get(2)->GetObject<Ipv4>();
  // “Tx” will fire when IP sends a packet down to the traffic-control layer
  ipv4_sender->TraceConnectWithoutContext("Tx", MakeCallback(&Ipv4TxTrace));

  // “Rx” will fire when IP receives a packet from the traffic-control layer
  ipv4_dest->TraceConnectWithoutContext("Rx", MakeCallback(&Ipv4RxTrace));

  // Flow
  uint16_t port = 7;
  Address localAddress(InetSocketAddress(Ipv4Address::GetAny(), port));
  PacketSinkHelper packetSinkHelper("ns3::TcpSocketFactory", localAddress);
  ApplicationContainer sinkApp = packetSinkHelper.Install(nodes.Get(2));

  sinkApp.Start(Seconds(0.0));
  sinkApp.Stop(Seconds(simulationTime));

  Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(payloadSize));

  Ptr<ComplexSendApplication> app = CreateObject<ComplexSendApplication>();

  app->SetAttribute(
      "Remote", AddressValue(InetSocketAddress(ifaces2.GetAddress(1), port)));
  app->SetAttribute("MaxBytes", UintegerValue(0)); // 0 means send indefinitely
  app->SetAttribute("MinSend", UintegerValue(MIN_SEND_RATE));
  app->SetAttribute("MaxSend", UintegerValue(MAX_SEND_RATE));
  // app->SetAttribute ("EndTime", TimeValue (Seconds (simEnd)));  // set the
  // stop time

  nodes.Get(0)->AddApplication(app);
  app->SetStartTime(Seconds(0.1));
  app->SetStopTime(Seconds(simEnd));

  // Ptr<ComplexSendApplication> bulkApp =
  //     DynamicCast<ComplexSendApplication>(apps.Get(0));
  // Simulator::Schedule(Seconds(simStart), &RandomizeSendSize, bulkApp,
  // sizeVar,
  //                     simEnd);

  // AsciiTraceHelper ascii;
  // pointToPoint1.EnableAsciiAll(
  //     ascii.CreateFileStream("wehe_sim_complex_n0-n1.tr"));
  // pointToPoint2.EnableAsciiAll(
  //     ascii.CreateFileStream("wehe_sim_complex_n1-n2.tr"));
  // pointToPoint1.EnablePcapAll("wehe_complex_n0-n1");
  // pointToPoint2.EnablePcapAll("wehe_complex_n1-n2");

  std::vector<std::string> args;
  // args.push_back(std::to_string(burst));
  // args.push_back(queueSize);
  assignFiles(pointToPoint1, pointToPoint2, "complex", args);

  Ptr<PacketSink> sink = DynamicCast<PacketSink>(sinkApp.Get(0));
  // double interval = 0.1; // Check throughput every 0.001 seconds
  // Simulator::Schedule(Seconds(interval), &ThroughputMonitor, sink, interval);

  Simulator::Stop(Seconds(simulationTime));
  Simulator::Run();

  Simulator::Destroy();

  double totalBytesReceived = sink->GetTotalRx(); // Get total received bytes
  double throughput =
      (totalBytesReceived * 8) / simulationTime; // Convert to bits per second
  droppedPacketsFile.close();
  std::ofstream metadata(getMetadataFileName("complex", args));
  metadata << throughput << std::endl;  // Log throughput in bps
  metadata << sums.size() << std::endl; // Log number of dropped packets
  metadata.close();

  std::cout << std::endl << "*** TC Layer statistics ***" << std::endl;
  std::cout << q->GetStats() << std::endl;

  std::cout << "IP-layer Tx Count (before queue disc): " << g_ipTxCount
            << std::endl;
  std::cout << "IP-layer Rx Count (after queue disc):  " << g_ipRxCount
            << std::endl;

  std::cout << std::endl << "*** Google paper estimation ***" << std::endl;
  std::cout << "Time between first and last loss: " << t_lastLoss - t_firstLoss
            << std::endl;
  std::cout << "The number of sums: " << sums.size() << std::endl;
  std::cout << "Bytes received in between first and last loss: "
            << sums[sums.size() - 1] << std::endl;
  std::cout << "Estimated goodput: "
            << sums[sums.size() - 1] / (t_lastLoss - t_firstLoss)
            << " B/s\t -> "
            << sums[sums.size() - 1] / (t_lastLoss - t_firstLoss) * 8 << " b/s"
            << std::endl;
  return 0;
}
