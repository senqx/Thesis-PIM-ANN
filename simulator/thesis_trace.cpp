// Project-owned replacement for the pinned upstream LoadStoreTrace frontend.
// Stop only after callbacks for every read; serialize query boundaries.
#include <fstream>
#include <sstream>
#include <limits>
#include "ramulator/base/param.h"
#include "ramulator/frontend/i_frontend.h"
namespace Ramulator {
class LoadStoreTrace : public IFrontEnd, public Implementation {
  RAMULATOR_REGISTER_IMPLEMENTATION(IFrontEnd, LoadStoreTrace, "LoadStoreTrace")
  struct Entry { Addr_t addr; uint64_t query; char kind; };
  std::vector<Entry> entries;
  size_t submitted=0, completed=0, peak_inflight=0;
  unsigned int max_inflight=64;
  std::string path, output, mapping_output;
  std::ofstream mappings;
  std::ofstream queries;
  Clk_t first=-1,last=-1;
  uint64_t count=0, query=0;
 public:
  void init() override {
    m_stats.add("submitted",submitted);
    m_stats.add("completed",completed);
    m_stats.add("peak_inflight",peak_inflight);
    RAMULATOR_PARSE_PARAM(m_clock_ratio, unsigned int, "clock_ratio").required();
    RAMULATOR_PARSE_PARAM(path, std::string, "path").required();
    RAMULATOR_PARSE_PARAM(output, std::string, "query_output").default_val("");
    RAMULATOR_PARSE_PARAM(mapping_output, std::string, "mapping_output").default_val("");
    RAMULATOR_PARSE_PARAM(max_inflight, unsigned int, "max_inflight").default_val(64);
    if(!m_clock_ratio || !max_inflight) throw std::runtime_error("zero clock ratio or inflight limit");
    std::ifstream in(path);
    if(!in)throw std::runtime_error("cannot open trace: "+path);
    std::string line;
    while(std::getline(in,line)) {
      std::istringstream row(line); std::string op, address, extra; uint64_t q=0; char kind='V';
      if(!(row>>op>>address) || op!="LD")throw std::runtime_error("expected LD address [query kind]");
      if(row>>extra) {
        size_t used=0;
        if(extra.empty() || extra[0]=='-')throw std::runtime_error("invalid query ID");
        q=std::stoull(extra,&used);
        if(used!=extra.size() || !(row>>kind) || (kind!='V' && kind!='A') || row>>extra)
          throw std::runtime_error("invalid query metadata");
      }
      size_t used=0;
      auto a=std::stoull(address,&used,0);
      if(address[0]=='-' || used!=address.size() || a>uint64_t(std::numeric_limits<Addr_t>::max()))
        throw std::runtime_error("invalid trace address");
      if(!entries.empty() && q<entries.back().query)throw std::runtime_error("query IDs must be increasing");
      entries.push_back({Addr_t(a),q,kind});
    }
    if(!in.eof() || entries.empty())throw std::runtime_error("empty or unreadable trace");
    if(!mapping_output.empty()) {
      mappings.open(mapping_output);
      if(!mappings)throw std::runtime_error("cannot open mapping output");
      mappings<<"address,channel,pseudochannel,sid,bankgroup,bank,row,column\n";
    }
    if(!output.empty()) {
      queries.open(output); if(!queries)throw std::runtime_error("cannot open query output");
      queries<<"query,reads,first_arrive,last_depart,cycles\n";
    }
  }
  void setup(IFrontEnd*, IMemorySystem* memory) override {
    if(memory->get_tx_bytes()!=32)throw std::runtime_error("thesis traces require 32-byte transactions");
    for(const auto& e:entries)if(e.addr%32)throw std::runtime_error("unaligned trace address");
  }
  void tick() override {
    if(++m_clk>10000000000LL)throw std::runtime_error("trace watchdog exceeded");
    if(submitted==entries.size() || submitted-completed>=max_inflight)return;
    const auto& e=entries[submitted];
    if(submitted && e.query!=entries[submitted-1].query) {
      if(completed!=submitted)return;
      finish_query();
    }
    Request req(e.addr,Request::Type::Read,0,[this](Request& r) {
      if(mappings.is_open()) {
        mappings<<r.addr;for(auto v:r.addr_vec)mappings<<','<<v;mappings<<'\n';
      }
      ++completed; first=first<0?r.arrive:std::min(first,r.arrive); last=std::max(last,r.depart);
    });
    req.size_bytes=32;
    if(m_memory_system->send(req)) { query=e.query; ++submitted; ++count; peak_inflight=std::max(peak_inflight,submitted-completed); }
  }
  bool is_finished() override { return completed==entries.size(); }
  void finish_query() {
    if(count && queries.is_open())queries<<query<<','<<count<<','<<first<<','<<last<<','<<last-first<<'\n';
    first=last=-1;count=0;
  }
  void finalize() override {
    if(submitted!=entries.size() || completed!=submitted)throw std::runtime_error("undrained trace");
    finish_query();
    if(mappings.is_open()){mappings.flush();if(!mappings)throw std::runtime_error("mapping output failed");}
    if(queries.is_open()) { queries.flush(); if(!queries)throw std::runtime_error("query output failed"); }
  }
};
}
