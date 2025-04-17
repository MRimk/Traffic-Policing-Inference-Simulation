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
#include "ns3/tcp-header.h"
#include "custom-send-application.h"

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

static std::vector<uint32_t> sums;

static void
Ipv4TxTrace (Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t interface)
{
  // Called whenever IP sends down a packet (before qdisc)
  g_ipTxCount++;
}

static void
Ipv4RxTrace (Ptr<const Packet> packet, Ptr<Ipv4> ipv4, uint32_t interface)
{
  // Called whenever IP receives a packet (after it’s demuxed up from L2)
  g_ipRxCount++;
  if(t_firstLoss > 0)
    sumRxBytes += packet->GetSize();
}

// void FirstBucketTokensTrace(uint32_t oldValue, uint32_t newValue) {
//   std::cout << "FirstBucketTokens " << oldValue << " to " << newValue
//             << std::endl;
// }

// void SecondBucketTokensTrace(uint32_t oldValue, uint32_t newValue) {
//   std::cout << "SecondBucketTokens " << oldValue << " to " << newValue
//             << std::endl;
// }


std::ofstream droppedPacketsFile("wehe-dropped-packets.txt");

void
PacketDropCallback (Ptr<const QueueDiscItem> item)
{
  double dropSeconds = Simulator::Now().GetSeconds();

  if(t_firstLoss < 0)
    t_firstLoss = dropSeconds;
  t_lastLoss = dropSeconds;
  sums.push_back(sumRxBytes); 

  TcpHeader tcpHeader;
  Ptr<const Packet> packet = item->GetPacket();
  if(packet->PeekHeader(tcpHeader))
    droppedPacketsFile << dropSeconds << "," << tcpHeader.GetSequenceNumber().GetValue() << "," << packet->GetSize() << std::endl;
  else
    droppedPacketsFile << dropSeconds << ",," << packet->GetSize() << std::endl;
}

// std::ofstream throughputFile("wehe-throughput.txt");

// void ThroughputMonitor(Ptr<PacketSink> sink, double interval) {
//   double bytesReceived = sink->GetTotalRx(); // Get total received bytes
//   static double lastBytes = 0;

//   double throughput =
//       ((bytesReceived - lastBytes) * 8) / interval; // Convert to bps
//   lastBytes = bytesReceived;

//   // Log time and throughput to file
//   throughputFile << Simulator::Now().GetSeconds() << " " << throughput / 1e6
//                  << std::endl;

//   // Schedule next measurement
//   Simulator::Schedule(Seconds(interval), &ThroughputMonitor, sink, interval);
// }

int main(int argc, char *argv[]) {
  double simulationTime = 10.2;  // seconds
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
  nodes.Create(3);

  PointToPointHelper pointToPoint1;
  pointToPoint1.SetDeviceAttribute("DataRate", StringValue("20Mb/s")); // link bandwidth
  pointToPoint1.SetChannelAttribute("Delay", StringValue("0ms"));

  PointToPointHelper pointToPoint2;
  pointToPoint2.SetDeviceAttribute("DataRate", StringValue("20Mb/s")); // link bandwidth
  pointToPoint2.SetChannelAttribute("Delay", StringValue("0ms"));

  NetDeviceContainer devices1 = pointToPoint1.Install(nodes.Get(0), nodes.Get(1));
  NetDeviceContainer devices2 = pointToPoint2.Install(nodes.Get(1), nodes.Get(2));

  InternetStackHelper stack;
  stack.Install(nodes);

  TrafficControlHelper tch;
  tch.SetRootQueueDisc("ns3::TbfQueueDisc",
                       "MaxSize", QueueSizeValue(QueueSize("1p")),
                       "Burst", UintegerValue(burst), "Mtu", UintegerValue(mtu),
                       "Rate", DataRateValue(DataRate(rate)), "PeakRate",
                       DataRateValue(DataRate(peakRate)));
  QueueDiscContainer qdiscs = tch.Install(devices2.Get(0));

  Ptr<QueueDisc> q = qdiscs.Get(0);
  q->SetMaxSize(ns3::QueueSize(ns3::QueueSizeUnit::PACKETS,1));
  // q->TraceConnectWithoutContext("TokensInFirstBucket",
  //                               MakeCallback(&FirstBucketTokensTrace));
  // q->TraceConnectWithoutContext("TokensInSecondBucket",
  //                               MakeCallback(&SecondBucketTokensTrace));
  q->TraceConnectWithoutContext("Drop", MakeCallback(&PacketDropCallback));
  
  // Assign IP addresses:
  //   10.1.1.x on n0 <-> n1
  //   10.1.2.x on n1 <-> n2
  Ipv4AddressHelper address1, address2;
  address1.SetBase("10.1.1.0", "255.255.255.0");
  address2.SetBase("10.1.2.0", "255.255.255.0");

  Ipv4InterfaceContainer ifaces1 = address1.Assign (devices1);
  Ipv4InterfaceContainer ifaces2 = address2.Assign (devices2);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables();

  Ptr<Ipv4> ipv4_sender = nodes.Get(1)->GetObject<Ipv4>();
  Ptr<Ipv4> ipv4_dest = nodes.Get(2)->GetObject<Ipv4>();
  // “Tx” will fire when IP sends a packet down to the traffic-control layer
  ipv4_sender->TraceConnectWithoutContext ("Tx", MakeCallback (&Ipv4TxTrace));

  // “Rx” will fire when IP receives a packet from the traffic-control layer
  ipv4_dest->TraceConnectWithoutContext ("Rx", MakeCallback (&Ipv4RxTrace));


  // Flow
  uint16_t port = 7;
  Address localAddress(InetSocketAddress(Ipv4Address::GetAny(), port));
  PacketSinkHelper packetSinkHelper("ns3::TcpSocketFactory", localAddress);
  ApplicationContainer sinkApp = packetSinkHelper.Install(nodes.Get(2));

  sinkApp.Start(Seconds(0.0));
  sinkApp.Stop(Seconds(simulationTime + 0.1));

  Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(payloadSize));


  Ptr<CustomIndexedSender> app = CreateObject<CustomIndexedSender> ();

  app->SetAttribute ("Remote", AddressValue(InetSocketAddress(ifaces2.GetAddress(1), port)));
  app->SetAttribute ("MaxBytes", UintegerValue (0));  // 0 means send indefinitely
  app->SetAttribute ("SendSize", UintegerValue(payloadSize)); // payloadSize should be 1448 bytes
  app->SetAttribute ("EndTime", TimeValue (Seconds (simulationTime - 0.1)));  // set the stop time

  nodes.Get(0)->AddApplication(app);
  app->SetStartTime(Seconds(0.1));
  app->SetStopTime(Seconds(simulationTime - 0.1));

  // BulkSendHelper bulkSend("ns3::TcpSocketFactory",
  //                         InetSocketAddress(ifaces2.GetAddress(1), port));
  // bulkSend.SetAttribute("MaxBytes", UintegerValue(0));
  // bulkSend.SetAttribute("SendSize", UintegerValue(payloadSize));

  // ApplicationContainer apps = bulkSend.Install(nodes.Get(0));
  // apps.Start(Seconds(0.1));
  // apps.Stop(Seconds(simulationTime - 0.1)); // need to cover the whole apps duration
  // TODO: ns3 identifier, when packet is lost, I can save the packet to a file
  // compute hash of data that uniquely identify the packet and match digest with the src ip, port, dest port, ip, sequence num
  // check if the payloads are different -- it's not different, as they are all 0's
  // add the middle node for the queueing -- DONE.
  // implement the google paper in ns3


  // Ptr<PacketSink> sink = DynamicCast<PacketSink>(sinkApp.Get(0));
  // double interval = 0.1; // Check throughput every 0.001 seconds
  // Simulator::Schedule(Seconds(interval), &ThroughputMonitor, sink, interval);

  // double totalBytesReceived = sink->GetTotalRx(); // Get total received bytes
  // double throughput =
  //     (totalBytesReceived * 8) / simulationTime; // Convert to bits per second

  // std::cout << std::endl << "*** Throughput Statistics ***" << std::endl;
  // std::cout << "Total Bytes Received: " << totalBytesReceived << " bytes"
  //           << std::endl;
  // std::cout << "Throughput: " << throughput / 1e6 << " Mbps" << std::endl;
  
  AsciiTraceHelper ascii;
  pointToPoint1.EnableAsciiAll (ascii.CreateFileStream ("wehe_sim_n0-n1.tr"));
  pointToPoint2.EnableAsciiAll (ascii.CreateFileStream ("wehe_sim_n1-n2.tr"));
  pointToPoint1.EnablePcapAll ("wehe_n0-n1");
  pointToPoint2.EnablePcapAll ("wehe_n1-n2");

  Simulator::Stop(Seconds(simulationTime + 5));
  Simulator::Run();

  Simulator::Destroy();

  // throughputFile.close();
  droppedPacketsFile.close();

  std::cout << std::endl << "*** TC Layer statistics ***" << std::endl;
  std::cout << q->GetStats() << std::endl;

  std::cout << "IP-layer Tx Count (before queue disc): " << g_ipTxCount << std::endl;
  std::cout << "IP-layer Rx Count (after queue disc):  " << g_ipRxCount << std::endl;

  std::cout << std::endl << "*** Google paper estimation ***" << std::endl;
  std::cout << "Time between first and last loss: " << t_lastLoss - t_firstLoss << std::endl;
  std::cout << "The number of sums: " << sums.size() << std::endl;
  std::cout << "Estimated goodput: " << sums[sums.size() - 1] / (t_lastLoss - t_firstLoss)  << " B/s\t -> " <<  sums[sums.size() - 1] / (t_lastLoss - t_firstLoss) * 8 << " b/s" << std::endl;
  return 0;
}
