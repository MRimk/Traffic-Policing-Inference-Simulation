#include "complex-send-app.h"
#include "ns3/address.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"
#include "ns3/node.h"
#include "ns3/nstime.h"
#include "ns3/packet.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/socket.h"
#include "ns3/tcp-socket-factory.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/uinteger.h"
#include "utils.h"

namespace ns3 {

TypeId ComplexSendApplication::GetTypeId(void) {
  static TypeId tid =
      TypeId("ns3::ComplexSendApplication")
          .SetParent<Application>()
          .AddConstructor<ComplexSendApplication>()
          .AddAttribute("UsePacketDistribution",
                        "Use the packet sizes extracted from trace",
                        BooleanValue(false),
                        MakeBooleanAccessor(
                            &ComplexSendApplication::m_sendPacketDistribution),
                        MakeBooleanChecker())
          .AddAttribute(
              "SendSize", "The amount of data to send each time.",
              UintegerValue(512),
              MakeUintegerAccessor(&ComplexSendApplication::m_sendSize),
              MakeUintegerChecker<uint32_t>(1))
          .AddAttribute(
              "MinSend", "Minimum amount of data to send each time randomly.",
              UintegerValue(0),
              MakeUintegerAccessor(&ComplexSendApplication::m_minPacket),
              MakeUintegerChecker<uint32_t>(1))
          .AddAttribute(
              "MaxSend", "Maximum amount of data to send each time randomly.",
              UintegerValue(0),
              MakeUintegerAccessor(&ComplexSendApplication::m_maxPacket),
              MakeUintegerChecker<uint32_t>(1))
          .AddAttribute("Remote", "The address of the destination",
                        AddressValue(),
                        MakeAddressAccessor(&ComplexSendApplication::m_peer),
                        MakeAddressChecker())
          .AddAttribute(
              "MaxBytes",
              "The total number of bytes to send. "
              "Once these bytes are sent, "
              "no data  is sent again. The value zero means "
              "that there is no limit.",
              UintegerValue(0),
              MakeUintegerAccessor(&ComplexSendApplication::m_maxBytes),
              MakeUintegerChecker<uint32_t>())
          .AddAttribute("Protocol", "The type of protocol to use.",
                        TypeIdValue(TcpSocketFactory::GetTypeId()),
                        MakeTypeIdAccessor(&ComplexSendApplication::m_tid),
                        MakeTypeIdChecker())
          .AddTraceSource(
              "Tx", "A new packet is created and is sent",
              MakeTraceSourceAccessor(&ComplexSendApplication::m_txTrace),
              "ns3::Packet::TracedCallback");
  return tid;
}

ComplexSendApplication::ComplexSendApplication()
    : m_socket(0), m_connected(false), m_totBytes(0) {}

ComplexSendApplication::~ComplexSendApplication() {}

void ComplexSendApplication::SetMaxBytes(uint32_t maxBytes) {
  m_maxBytes = maxBytes;
}

Ptr<Socket> ComplexSendApplication::GetSocket(void) const { return m_socket; }

void ComplexSendApplication::DoDispose(void) {
  m_socket = 0;
  // chain up
  Application::DoDispose();
}

// Application Methods
void ComplexSendApplication::StartApplication(
    void) // Called at time specified by Start
{
  if (m_sendPacketDistribution && m_packetSizes.empty()) {
    // Read the packet sizes from the file
    m_packetSizes = getPacketSizes();
    if (m_packetSizes.empty()) {
      NS_FATAL_ERROR("No packet sizes found in the file.");
    }
  }

  // Create the socket if not already
  if (!m_socket) {
    m_socket = Socket::CreateSocket(GetNode(), m_tid);

    // Fatal error if socket type is not NS3_SOCK_STREAM or NS3_SOCK_SEQPACKET
    if (m_socket->GetSocketType() != Socket::NS3_SOCK_STREAM &&
        m_socket->GetSocketType() != Socket::NS3_SOCK_SEQPACKET) {
      NS_FATAL_ERROR("Using BulkSend with an incompatible socket type. "
                     "BulkSend requires SOCK_STREAM or SOCK_SEQPACKET. "
                     "In other words, use TCP instead of UDP.");
    }

    if (Inet6SocketAddress::IsMatchingType(m_peer)) {
      m_socket->Bind6();
    } else if (InetSocketAddress::IsMatchingType(m_peer)) {
      m_socket->Bind();
    }
    // m_socket->SetAttribute("SegmentSize", UintegerValue(m_maxPacket));
    // m_socket->SetAttribute("TcpNoDelay", BooleanValue(true));

    m_sizeVar = CreateObject<UniformRandomVariable>();

    m_socket->Connect(m_peer);
    m_socket->SetAllowBroadcast(true);
    m_socket->ShutdownRecv();
    m_socket->SetConnectCallback(
        MakeCallback(&ComplexSendApplication::ConnectionSucceeded, this),
        MakeCallback(&ComplexSendApplication::ConnectionFailed, this));
    m_socket->SetSendCallback(
        MakeCallback(&ComplexSendApplication::DataSend, this));
  }
  if (m_connected) {
    SendData();
  }
}

void ComplexSendApplication::StopApplication(
    void) // Called at time specified by Stop
{

  if (m_socket) {
    m_socket->Close();
    m_connected = false;
  } else {
    std::cout << "ComplexSendApplication found null socket to close in "
                 "StopApplication"
              << std::endl;
  }
}

// Private helpers

void ComplexSendApplication::SendData(void) {
  while (m_maxBytes == 0 || m_totBytes < m_maxBytes) { // Time to send more
    uint32_t toSend = m_sendSize;

    if (m_sendPacketDistribution) {
      // Use the packet sizes extracted from trace
      toSend = m_packetSizes[m_seq % m_packetSizes.size()];
    } else if (m_maxPacket > 0) {
      toSend = m_sizeVar->GetInteger(m_minPacket, m_maxPacket);
    }

    toSend =
        (m_maxBytes > 0) ? std::min(toSend, m_maxBytes - m_totBytes) : toSend;
    // std::cout << "sending packet at " << Simulator::Now() << std::endl;
    Ptr<Packet> packet = Create<Packet>(toSend);

    SeqTsHeader seqTs;
    seqTs.SetSeq(m_seq++);
    toSend = toSend > (8 + 4) ? toSend - (8 + 4)
                              : toSend; // 8+4 : the size of the seqTs header
    if (toSend > (8 + 4)) {
      packet->AddHeader(seqTs);
    }

    m_txTrace(packet);
    int actual = m_socket->Send(packet);
    if (actual > 0) {
      // std::cout << "actual send size: " << actual << std::endl;
      m_totBytes += actual;
    }

    // We exit this loop when actual < toSend as the send side
    // buffer is full. The "DataSent" callback will pop when
    // some buffer space has freed ip.
    if ((unsigned)actual != toSend) {
      break;
    }
  }
  // Check if time to close (all sent)
  if (m_totBytes == m_maxBytes && m_connected) {
    m_socket->Close();
    m_connected = false;
  }
}

void ComplexSendApplication::ConnectionSucceeded(Ptr<Socket> socket) {
  m_connected = true;
  SendData();
}

void ComplexSendApplication::ConnectionFailed(Ptr<Socket> socket) {}

void ComplexSendApplication::DataSend(Ptr<Socket>, uint32_t) {
  if (m_connected) { // Only send new data if the connection has completed
    Simulator::ScheduleNow(&ComplexSendApplication::SendData, this);
  }
}

} // Namespace ns3