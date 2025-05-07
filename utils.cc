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
