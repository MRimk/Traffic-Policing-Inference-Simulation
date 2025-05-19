#include "ns3/point-to-point-module.h"
#include <string.h>
#include <vector>

using namespace ns3;

void assignFiles(PointToPointHelper pp1, PointToPointHelper pp2,
                 std::string name, std::vector<std::string> &args);

std::string getFilename(std::string fileContent, std::string simName,
                        std::vector<std::string> &args);

std::string getMetadataFileName(std::string simName,
                                std::vector<std::string> &args);

std::vector<uint32_t> readSizes(const std::string &filename);

std::vector<uint32_t> getPacketSizes();