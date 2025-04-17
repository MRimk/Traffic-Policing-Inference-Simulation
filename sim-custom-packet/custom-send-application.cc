// https://www.youtube.com/watch?v=aJxM1P9XLCQ&ab_channel=AdilAlsuhaim

#include "custom-send-application.h"


CustomIndexedSender::CustomIndexedSender ()
: m_socket (0),
  m_totBytes (0),
  m_packetIndex (1)
{
}

CustomIndexedSender::~CustomIndexedSender()
{
  m_socket = 0;
}

TypeId CustomIndexedSender::GetTypeId (void)
  {
    static TypeId tid = TypeId ("CustomIndexedSender")
      .SetParent<Application> ()
      .SetGroupName ("Tutorial")
      .AddConstructor<CustomIndexedSender> ()
      .AddAttribute ("Remote",
                     "The address of the destination",
                     AddressValue (),
                     MakeAddressAccessor (&CustomIndexedSender::m_peer),
                     MakeAddressChecker ())
      .AddAttribute ("MaxBytes",
                     "The total number of bytes to send (0 means unlimited)",
                     UintegerValue (0),
                     MakeUintegerAccessor (&CustomIndexedSender::m_maxBytes),
                     MakeUintegerChecker<uint64_t> ())
      .AddAttribute ("SendSize",
                     "The size of each packet sent, in bytes (should be 1448 for MSS)",
                     UintegerValue (1448),
                     MakeUintegerAccessor (&CustomIndexedSender::m_sendSize),
                     MakeUintegerChecker<uint32_t> ())
      .AddAttribute ("EndTime",
                      "The time at which the application will stop sending data",
                      TimeValue (Seconds (10.0)), // default value, can be set by the user
                      MakeTimeAccessor (&CustomIndexedSender::m_stopTime),
                      MakeTimeChecker ());
    return tid;
  }

  void CustomIndexedSender::SendData ()
  {
    if (Simulator::Now() >= m_stopTime)
      {
        std::cout << "More than stop time" << std::endl;

        return;
      }

    if (m_maxBytes > 0 && m_totBytes >= m_maxBytes)
      {
        return; // finished sending the specified amount of data
      }

    uint32_t sendSize = m_sendSize;
    // If a max bytes limit is set, adjust the send size accordingly.
    if (m_maxBytes > 0 && (m_totBytes + sendSize) > m_maxBytes)
      {
        sendSize = m_maxBytes - m_totBytes;
      }
    
    // Create a buffer of fixed size and initialize it with zeros.
    std::vector<uint8_t> buffer(sendSize, 0);

    // Convert the current packet index into a string.
    std::string indexStr = std::to_string(m_packetIndex);
    // You might want to pad the string to a fixed width or insert a delimiter if needed.
    // Here we simply copy it into the beginning of the buffer.
    std::copy(indexStr.begin(), indexStr.end(), buffer.begin());

    // Create a packet from the buffer.
    Ptr<Packet> packet = Create<Packet> (buffer.data(), sendSize);
    int actual = m_socket->Send (packet);
    // NS_LOG_INFO ("Sent packet " << m_packetIndex << " (" << actual << " bytes)");
    // std::cout << "Sent packet " << m_packetIndex << " (" << actual << " bytes)" << std::endl;
    m_totBytes += actual;
    m_packetIndex++;

    // Schedule the next packet send (here we do it immediately; you can add a delay as needed)
    m_sendEvent = Simulator::Schedule (Seconds (0.0001), &CustomIndexedSender::SendData, this);
  }

  void CustomIndexedSender::StartApplication (void)
  {
    // Create and connect the socket.
    if (!m_socket)
      {
        m_socket = Socket::CreateSocket (GetNode (), TypeId::LookupByName ("ns3::TcpSocketFactory"));
        m_socket->Connect (m_peer);
      }
    SendData ();
  }

  void CustomIndexedSender::StopApplication (void)
  {
    std::cout << "Stop application called" << std::endl;
    if (m_socket)
      {
        m_socket->Close ();
        m_socket = 0;
      }
    Simulator::Cancel (m_sendEvent);
  }