#include "utils.h"
#include "ns3/point-to-point-module.h"

void assignFiles(PointToPointHelper pp1, PointToPointHelper pp2,
                 std::string name, std::vector<std::string> &args) {
  AsciiTraceHelper ascii;

  std::string traceFileNameBase =
      "scratch/Traffic-Policing-Inference-Simulation/data/wehe_sim_";
  std::string clientSide = "n0-n1";
  std::string serverSide = "n1-n2";
  std::ostringstream traceFileNameStream;

  traceFileNameStream << traceFileNameBase << name << "_";
  for (auto &arg : args) {
    traceFileNameStream << arg << "_";
  }

  traceFileNameStream << serverSide;
  std::string pcapServerSide = traceFileNameStream.str();
  traceFileNameStream << ".tr";
  std::string traceFileServer = traceFileNameStream.str();

  traceFileNameStream.str(""); // reset buffer
  traceFileNameStream.clear();

  traceFileNameStream << traceFileNameBase << name << "_";
  for (auto &arg : args) {
    traceFileNameStream << arg << "_";
  }

  traceFileNameStream << clientSide;
  std::string pcapClientSide = traceFileNameStream.str();
  traceFileNameStream << ".tr";
  std::string traceFileClient = traceFileNameStream.str();

  pp1.EnableAsciiAll(ascii.CreateFileStream(traceFileServer));
  pp2.EnableAsciiAll(ascii.CreateFileStream(traceFileClient));
  pp1.EnablePcapAll(pcapServerSide);
  pp2.EnablePcapAll(pcapClientSide);
}

std::string getFilename(std::string fileContent, std::string simName,
                        std::vector<std::string> &args) {
  std::string fileNameBase =
      "scratch/Traffic-Policing-Inference-Simulation/data/wehe_";
  std::ostringstream fileNameStream;

  fileNameStream << fileNameBase << fileContent << "_" << simName << "_";
  for (auto &arg : args) {
    fileNameStream << arg << "_";
  }
  return fileNameStream.str();
}

std::string getMetadataFileName(std::string simName,
                                std::vector<std::string> &args) {
  return getFilename("metadata", simName, args);
}

std::vector<uint32_t> readSizes(const std::string &filename) {
  std::vector<uint32_t> sizes;
  std::ifstream file(filename);
  if (!file.is_open()) {
    throw std::runtime_error("Could not open file: " + filename);
  }

  std::string line;
  // Skip header
  if (!std::getline(file, line)) {
    // Empty file (or inaccessible); return empty vector
    return sizes;
  }

  // Read each line, parse to uint32_t, and collect
  while (std::getline(file, line)) {
    if (line.empty())
      continue; // skip blank lines
    try {
      auto s = static_cast<uint32_t>(std::stoul(line));
      sizes.push_back(s);
    } catch (const std::exception &e) {
      // You could log or handle malformed lines here
      throw std::runtime_error("Invalid number in line: " + line);
    }
  }

  return sizes;
}

std::vector<uint32_t> getPacketSizes() {
  return readSizes("scratch/Traffic-Policing-Inference-Simulation/send_data/"
                   "youtube_packets.csv");
}

void getTracerFiles(std::string simName, std::vector<std::string> &args,
                    std::ofstream &cwndFile, std::ofstream &rttFile,
                    std::ofstream &rtoFile) {
  cwndFile.open(getFilename("cwnd", simName, args));
  rttFile.open(getFilename("rtt", simName, args));
  rtoFile.open(getFilename("rto", simName, args));
}