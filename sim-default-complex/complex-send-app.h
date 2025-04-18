#include "ns3/address.h"
#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/ptr.h"
#include "ns3/random-variable-stream.h"
#include "ns3/traced-callback.h"

namespace ns3 {

class Address;
class Socket;

class ComplexSendApplication : public Application {
public:
  static TypeId GetTypeId(void);

  ComplexSendApplication();

  virtual ~ComplexSendApplication();

  void SetMaxBytes(uint32_t maxBytes);

  Ptr<Socket> GetSocket(void) const;

protected:
  virtual void DoDispose(void);

private:
  // inherited from Application base class.
  virtual void StartApplication(void); // Called at time specified by Start
  virtual void StopApplication(void);  // Called at time specified by Stop

  void SendData();

  Ptr<Socket> m_socket;
  Address m_peer;
  bool m_connected;
  uint32_t m_sendSize;
  uint32_t m_maxBytes;
  uint32_t m_totBytes;
  uint32_t m_minPacket;
  uint32_t m_maxPacket;
  TypeId m_tid;
  Ptr<UniformRandomVariable> m_sizeVar;

  TracedCallback<Ptr<const Packet>> m_txTrace;

private:
  void ConnectionSucceeded(Ptr<Socket> socket);
  void ConnectionFailed(Ptr<Socket> socket);
  void DataSend(Ptr<Socket>, uint32_t); // for socket's SetSendCallback
};

} // namespace ns3
