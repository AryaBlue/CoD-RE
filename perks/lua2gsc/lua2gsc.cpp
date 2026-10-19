// lua2gsc command line: compiles ZM Workshop Lua perks into one Plutonium T6 script.
//   lua2gsc <runtime.gsc> <out.gsc> <perk.lua>...
// The perk id is the file name (vampire.lua -> vampire). Errors print as file:line: message.
#include "lua2gsc.h"
#include <fstream>
#include <iostream>
#include <sstream>

static bool Read(const std::string& path, std::string& text) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    std::stringstream s; s << f.rdbuf(); text = s.str();
    return true;
}

int main(int argc, char** argv) {
    if (argc < 4) { std::cerr << "usage: lua2gsc <runtime.gsc> <out.gsc> <perk.lua>...\n"; return 2; }
    std::string runtime;
    if (!Read(argv[1], runtime)) { std::cerr << argv[1] << ": can't read\n"; return 2; }
    std::vector<lua2gsc::Result> perks;
    int failed = 0;
    for (int i = 3; i < argc; ++i) {
        std::string path = argv[i], src;
        if (!Read(path, src)) { std::cerr << path << ": can't read\n"; ++failed; continue; }
        size_t slash = path.find_last_of("/\\"), dot = path.rfind('.');
        std::string id = path.substr(slash == std::string::npos ? 0 : slash + 1);
        if (dot != std::string::npos && dot > path.size() - id.size()) id = id.substr(0, id.size() - (path.size() - dot));
        lua2gsc::Result r = lua2gsc::Compile(src, id);
        if (!r.ok) { std::cerr << path << ": " << r.error << "\n"; ++failed; continue; }
        std::cout << "compiled " << id << " (" << r.name << ")\n";
        perks.push_back(r);
    }
    std::ofstream out(argv[2], std::ios::binary);
    out << lua2gsc::Bundle(runtime, perks);
    return failed ? 1 : 0;
}
