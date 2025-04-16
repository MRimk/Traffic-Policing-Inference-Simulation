#pragma once
#include "ns3/application.h"
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/socket.h"
#include "ns3/simulator.h"
#include "ns3/nstime.h"
#include <vector>
#include <string>
#include <algorithm>

using namespace ns3;

class CustomIndexedSender : public Application
{
public:
  static TypeId GetTypeId (void);

  CustomIndexedSender ();
  ~CustomIndexedSender();

  void SendData ();

protected:
  virtual void StartApplication (void);
  virtual void StopApplication (void);

private:
  Ptr<Socket> m_socket;
  Address m_peer;
  uint32_t m_sendSize;  // size of each packet (e.g., 1448 bytes)
  uint64_t m_maxBytes;  // total number of bytes to send (0 means unlimited)
  uint64_t m_totBytes;  // total bytes sent so far
  EventId m_sendEvent;
  uint32_t m_packetIndex;  // counter to embed into the payload
  Time m_stopTime;         // stores the stop time set via attribute
};
