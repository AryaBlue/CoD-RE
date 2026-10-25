// Reference VM for lua2gsc live bytecode: runs a perk the way zmwi_run in zm_workshop_perks.gsc does (GSC value rules:
// arrays are copied, structs and entities are references, + joins strings, 0 is false) against a small mock world.
//   livevm <perk.lua>      compiles with CompileLive, runs on_give + on_hit, prints what the perk printed
// tests/live/lua/main.lua runs the same perk in real Lua with the same world; the outputs must match.
// build: cl /EHsc /std:c++17 /I../lua2gsc livevm.cpp   (lua2gsc.h lives in ../lua2gsc in CoD-RE)
#include "lua2gsc.h"
#include <cmath>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>

struct Val; struct Arr; struct Rec; struct Ent;
struct Key { bool isInt = true; long long i = 0; std::string s; bool operator==(const Key& o) const { return isInt == o.isInt && i == o.i && s == o.s; } };
struct Val {
    enum T { NIL, INT, FLT, STR, ARR, REC, ENT, FN, VEC } t = NIL;
    long long i = 0; double f = 0; std::string s;
    std::shared_ptr<Arr> arr; std::shared_ptr<Rec> rec; std::shared_ptr<Ent> ent; double v[3] = {};
    Val() {}
    Val(const Val& o);
    Val& operator=(const Val& o);
    static Val Int(long long x) { Val r; r.t = INT; r.i = x; return r; }
    static Val Flt(double x) { Val r; r.t = FLT; r.f = x; return r; }
    static Val Str(const std::string& x) { Val r; r.t = STR; r.s = x; return r; }
    double Num() const { return t == INT ? (double)i : f; }
};
struct Arr { std::vector<std::pair<Key, Val>> items; };   // insertion order, like getarraykeys (reversed there; order isn't relied on)
struct Rec { Arr f; };
struct Ent { std::string name; long long hp = 0, points = 500; Arr fields; };
Val::Val(const Val& o) { *this = o; }
Val& Val::operator=(const Val& o) {
    if (this == &o) return *this;
    t = o.t; i = o.i; f = o.f; s = o.s; rec = o.rec; ent = o.ent; v[0] = o.v[0]; v[1] = o.v[1]; v[2] = o.v[2];
    arr = o.arr ? std::make_shared<Arr>(*o.arr) : nullptr;   // arrays are values in GSC
    return *this;
}
static Val* Find(Arr& a, const Key& k) { for (auto& kv : a.items) if (kv.first == k) return &kv.second; return nullptr; }
static void Set(Arr& a, const Key& k, const Val& v) {
    for (size_t j = 0; j < a.items.size(); ++j) if (a.items[j].first == k) {
        if (v.t == Val::NIL) a.items.erase(a.items.begin() + j); else a.items[j].second = v;
        return;
    }
    if (v.t != Val::NIL) a.items.push_back({k, v});
}
static Key KeyOf(const Val& v, bool shift) {
    Key k;
    if (v.t == Val::STR) { k.isInt = false; k.s = v.s; } else { k.i = v.t == Val::INT ? v.i : (long long)v.f; if (shift && v.t == Val::INT) k.i -= 1; }
    return k;
}
static Key Name(const std::string& n) { Key k; k.isInt = false; k.s = n; return k; }

static std::string Unesc(const std::string& s) {
    std::string o;
    for (size_t j = 0; j < s.size(); ++j)
        if (s[j] == '%' && j + 2 < s.size()) { o += (char)strtol(s.substr(j + 1, 2).c_str(), nullptr, 16); j += 2; } else o += s[j];
    return o;
}
static Val ConstOf(const std::string& tok) {
    if (tok == "u") return Val();
    if (tok[0] == 'i') return Val::Int(atoll(tok.c_str() + 1));
    if (tok[0] == 'n') return Val::Flt(atof(tok.c_str() + 1));
    return Val::Str(Unesc(tok.substr(1)));
}
static std::string Text(const Val& v) {
    char b[64];
    switch (v.t) {
    case Val::INT: return std::to_string(v.i);
    case Val::FLT: snprintf(b, sizeof b, "%g", v.f); return b;
    case Val::STR: return v.s;
    case Val::NIL: return "";
    default: return "<obj>";
    }
}
static bool Truthy(const Val& v) {
    if (v.t == Val::NIL) return false;
    if (v.t == Val::INT) return v.i != 0;
    if (v.t == Val::FLT) return v.f != 0;
    return true;
}
static bool Eq(const Val& a, const Val& b) {
    if (a.t == Val::NIL || b.t == Val::NIL) return a.t == b.t;
    if ((a.t == Val::STR) != (b.t == Val::STR)) return false;
    if (a.t == Val::STR) return a.s == b.s;
    if ((a.t == Val::INT || a.t == Val::FLT) && (b.t == Val::INT || b.t == Val::FLT)) return a.Num() == b.Num();
    if (a.t == Val::ENT && b.t == Val::ENT) return a.ent == b.ent;
    if (a.t == Val::REC && b.t == Val::REC) return a.rec == b.rec;
    return false;
}

struct Fn { int params = 0, regs = 0; std::vector<std::vector<std::string>> code; };
struct Perk { std::string id; Arr info; std::vector<Fn> fns; std::map<std::string, int> handlers; Arr globals; std::shared_ptr<Rec> rec; };

static Perk Load(const std::string& ir) {
    std::vector<std::string> t; { std::istringstream ss(ir); std::string w; while (ss >> w) t.push_back(w); }
    Perk p; size_t at = 3; p.id = t[2]; p.rec = std::make_shared<Rec>();
    auto put = [&](const std::string& k, const Val& v) { Set(p.rec->f, Name(k), v); };
    put("id", Val::Str(p.id));
    while (at < t.size()) {
        const std::string& w = t[at++];
        if (w == "I") { std::string k = t[at++]; put(k, ConstOf(t[at++])); }
        else if (w == "C") { Val c; c.t = Val::VEC; for (int j = 0; j < 3; ++j) c.v[j] = ConstOf(t[at++]).Num(); put("color", c); }
        else if (w == "M") {
            std::string map = Unesc(t[at++]); int n = atoi(t[at++].c_str());
            Val list; list.t = Val::ARR; list.arr = std::make_shared<Arr>();
            for (int j = 0; j < n; ++j) Set(*list.arr, Key{true, j}, ConstOf(t[at++]));
            Val* m = Find(p.rec->f, Name("machines"));
            Val ms; if (m) ms = *m; else { ms.t = Val::ARR; ms.arr = std::make_shared<Arr>(); }
            Set(*ms.arr, Name(map), list); put("machines", ms);
        } else if (w == "S") {
            int n = atoi(t[at++].c_str());
            Val list; list.t = Val::ARR; list.arr = std::make_shared<Arr>();
            for (int j = 0; j < n; ++j) Set(*list.arr, Key{true, j}, ConstOf(t[at++]));
            put("specialties", list);
        } else if (w == "F") {
            Fn f; f.params = atoi(t[at++].c_str()); f.regs = atoi(t[at++].c_str()); int n = atoi(t[at++].c_str());
            static const std::map<std::string, int> fixed = {{"K", 2}, {"MV", 2}, {"GG", 2}, {"GS", 2}, {"FN", 2}, {"PK", 1}, {"GF", 3}, {"SF", 3},
                {"GI", 3}, {"SI", 3}, {"NL", 1}, {"NR", 1}, {"NOT", 2}, {"NEG", 2}, {"LEN", 2}, {"J", 1}, {"JF", 2}, {"JT", 2}, {"W", 1}, {"R", 1}, {"R0", 0}};
            for (int j = 0; j < n; ++j) {
                std::vector<std::string> ins{t[at++]};
                const std::string& op = ins[0];
                int argc;
                if (fixed.count(op)) argc = fixed.at(op);
                else if (op == "CA" || op == "CF" || op == "CV") argc = 3 + atoi(t[at + 2].c_str());
                else if (op == "CM") argc = 4 + atoi(t[at + 3].c_str());
                else if (op == "TH") argc = 2 + atoi(t[at + 1].c_str());
                else argc = 3;                                // binary ops
                for (int k = 0; k < argc; ++k) ins.push_back(t[at++]);
                f.code.push_back(ins);
            }
            p.fns.push_back(f);
        } else if (w == "H") { std::string h = t[at++]; p.handlers[h] = atoi(t[at++].c_str()); }
        else if (w == "E") break;
        else { std::cerr << "bad token " << w << "\n"; exit(3); }
    }
    return p;
}

// ---- mock world (tests/live/lua/main.lua has the same)
static std::shared_ptr<Ent> g_host, g_z1, g_z2;
static Val E(const std::shared_ptr<Ent>& e) { Val v; v.t = Val::ENT; v.ent = e; return v; }
static Val List(std::vector<Val> items) { Val v; v.t = Val::ARR; v.arr = std::make_shared<Arr>(); for (size_t j = 0; j < items.size(); ++j) Set(*v.arr, Key{true, (long long)j}, items[j]); return v; }

static Val Run(Perk& p, int fi, std::vector<Val> args);

static Val Api(Perk& p, const std::string& n, std::vector<Val>& a) {
    auto arg = [&](size_t j) { return j < a.size() ? a[j] : Val(); };
    if (n == "print") { std::cout << "PRINT " << Text(arg(0)) << "\n"; return Val(); }
    if (n == "tostring") return arg(0).t == Val::NIL ? Val::Str("nil") : Val::Str(Text(arg(0)));
    if (n == "round_number") return Val::Int(5);
    if (n == "zombies_near" || n == "zombies") return List({E(g_z1), E(g_z2)});
    if (n == "players") return List({E(g_host)});
    if (n == "min" || n == "math.min") return arg(0).Num() < arg(1).Num() ? arg(0) : arg(1);
    if (n == "max" || n == "math.max") return arg(0).Num() > arg(1).Num() ? arg(0) : arg(1);
    if (n == "floor" || n == "math.floor") return Val::Flt(std::floor(arg(0).Num()));
    if (n == "string.lower") { std::string s = arg(0).s; for (char& c : s) c = (char)tolower((unsigned char)c); return Val::Str(s); }
    if (n == "string.sub") { long long i = arg(1).i, j = a.size() > 2 ? arg(2).i : (long long)arg(0).s.size(); return Val::Str(arg(0).s.substr(i - 1, j - i + 1)); }
    if (n == "string.find") return Val::Int(arg(0).s.find(arg(1).s) != std::string::npos);
    if (n == "__keys") { Val t = arg(0); std::vector<Val> k; for (auto& kv : t.arr->items) k.push_back(kv.first.isInt ? Val::Int(kv.first.i) : Val::Str(kv.first.s)); return List(k); }
    if (n == "__keyout") return arg(0).t == Val::INT ? Val::Int(arg(0).i + 1) : arg(0);
    if (n == "__remove") {
        Val t = arg(0), out = List({}); long long k = 0, drop = arg(1).i - 1, j = 0;
        for (auto& kv : t.arr->items) { if (j++ != drop) Set(*out.arr, Key{true, k++}, kv.second); }
        return out;
    }
    std::cerr << "mock: no API " << n << "\n"; exit(4);
}
static Val Method(Perk& p, const std::string& n, Val& o, std::vector<Val>& a) {
    Ent& e = *o.ent;
    if (n == "name") return Val::Str(e.name);
    if (n == "points") return Val::Int(e.points);
    if (n == "give_points") { e.points += (long long)a[0].Num(); return Val(); }
    if (n == "health") return Val::Int(e.hp);
    if (n == "origin") { Val v; v.t = Val::VEC; return v; }
    if (n == "damage") { e.hp -= (long long)a[0].Num(); return Val(); }
    if (n == "print") { std::cout << "[" << e.name << "] " << Text(a[0]) << "\n"; return Val(); }
    std::cerr << "mock: no method " << n << "\n"; exit(4);
}

static Val Arith(const std::string& op, const Val& a, const Val& b) {
    if (op == "ADD" && (a.t == Val::STR || b.t == Val::STR)) return Val::Str(Text(a) + Text(b));
    bool fl = a.t == Val::FLT || b.t == Val::FLT;
    double x = a.Num(), y = b.Num();
    if (op == "ADD") return fl ? Val::Flt(x + y) : Val::Int(a.i + b.i);
    if (op == "SUB") return fl ? Val::Flt(x - y) : Val::Int(a.i - b.i);
    if (op == "MUL") return fl ? Val::Flt(x * y) : Val::Int(a.i * b.i);
    if (op == "DIV") return Val::Flt(x * 1.0 / y);
    if (op == "IDIV") { double q = x / y; long long f = (long long)q; if (f > q) --f; return Val::Int(f); }
    if (op == "MOD") return Val::Int(a.i % b.i);
    if (op == "POW") { Val r = Val::Int(1); for (long long k = 0; k < (long long)y; ++k) r = Arith("MUL", r, a); return r; }
    if (op == "LT") return Val::Int(x < y);
    if (op == "GT") return Val::Int(x > y);
    if (op == "LE") return Val::Int(x <= y);
    if (op == "GE") return Val::Int(x >= y);
    if (op == "EQ") return Val::Int(Eq(a, b));
    if (op == "NE") return Val::Int(!Eq(a, b));
    if (op == "CAT") return Val::Str(Text(a) + Text(b));
    std::cerr << "bad op " << op << "\n"; exit(5);
}

static Val GetField(Perk& p, const Val& o, const Key& k) {
    if (o.t == Val::ENT) { Val* v = Find(o.ent->fields, k); return v ? *v : Val(); }
    if (o.t == Val::REC) { Val* v = Find(o.rec->f, k); return v ? *v : Val(); }
    if (o.t == Val::ARR) { Val* v = Find(*o.arr, k); return v ? *v : Val(); }
    return Val();
}
static void SetField(Val& o, const Key& k, const Val& v) {
    if (o.t == Val::ENT) Set(o.ent->fields, k, v);
    else if (o.t == Val::REC) Set(o.rec->f, k, v);
    else if (o.t == Val::ARR) Set(*o.arr, k, v);
}

static Val Run(Perk& p, int fi, std::vector<Val> args) {
    Fn& f = p.fns[fi];
    std::vector<Val> r(f.regs + 1);
    for (int j = 0; j < f.params && j < (int)args.size(); ++j) r[j] = args[j];
    auto R = [&](const std::string& s) -> Val& { return r[atoi(s.c_str())]; };
    for (size_t pc = 0; pc < f.code.size();) {
        auto& ins = f.code[pc++];
        const std::string& op = ins[0];
        auto callArgs = [&](size_t from) { std::vector<Val> a; int n = atoi(ins[from].c_str()); for (int j = 0; j < n; ++j) a.push_back(R(ins[from + 1 + j])); return a; };
        if (op == "K") R(ins[1]) = ConstOf(ins[2]);
        else if (op == "MV") { Val v = R(ins[2]); R(ins[1]) = v; }
        else if (op == "GG") { Val* v = Find(p.globals, Name(Unesc(ins[2]))); R(ins[1]) = v ? *v : Val(); }
        else if (op == "GS") Set(p.globals, Name(Unesc(ins[1])), R(ins[2]));
        else if (op == "FN") { Val v; v.t = Val::FN; v.i = atoi(ins[2].c_str()); R(ins[1]) = v; }
        else if (op == "PK") { Val v; v.t = Val::REC; v.rec = p.rec; R(ins[1]) = v; }
        else if (op == "GF") R(ins[1]) = GetField(p, R(ins[2]), Name(Unesc(ins[3])));
        else if (op == "SF") SetField(R(ins[1]), Name(Unesc(ins[2])), R(ins[3]));
        else if (op == "GI") R(ins[1]) = GetField(p, R(ins[2]), KeyOf(R(ins[3]), true));
        else if (op == "SI") { Val v = R(ins[3]); SetField(R(ins[1]), KeyOf(R(ins[2]), true), v); }
        else if (op == "NL") { Val v; v.t = Val::ARR; v.arr = std::make_shared<Arr>(); R(ins[1]) = v; }
        else if (op == "NR") { Val v; v.t = Val::REC; v.rec = std::make_shared<Rec>(); R(ins[1]) = v; }
        else if (op == "NOT") R(ins[1]) = Val::Int(!Truthy(R(ins[2])));
        else if (op == "NEG") R(ins[1]) = Arith("SUB", Val::Int(0), R(ins[2]));
        else if (op == "LEN") { Val& a = R(ins[2]); R(ins[1]) = Val::Int(a.t == Val::ARR ? (long long)a.arr->items.size() : (long long)a.s.size()); }
        else if (op == "J") pc = atoi(ins[1].c_str());
        else if (op == "JF") { if (!Truthy(R(ins[1]))) pc = atoi(ins[2].c_str()); }
        else if (op == "JT") { if (Truthy(R(ins[1]))) pc = atoi(ins[2].c_str()); }
        else if (op == "CA") { auto a = callArgs(3); R(ins[1]) = Api(p, Unesc(ins[2]), a); }
        else if (op == "CM") { auto a = callArgs(4); R(ins[1]) = Method(p, Unesc(ins[2]), R(ins[3]), a); }
        else if (op == "CF") R(ins[1]) = Run(p, atoi(ins[2].c_str()), callArgs(3));
        else if (op == "CV") { Val fv = R(ins[2]); R(ins[1]) = Run(p, (int)fv.i, callArgs(3)); }
        else if (op == "TH") Run(p, atoi(ins[1].c_str()), callArgs(2));
        else if (op == "W") {}
        else if (op == "R") return R(ins[1]);
        else if (op == "R0") return Val();
        else { Val v = Arith(op, R(ins[2]), R(ins[3])); R(ins[1]) = v; }
    }
    return Val();
}

int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "usage: livevm <perk.lua> [--dump]\n"; return 2; }
    std::ifstream in(argv[1], std::ios::binary); std::stringstream ss; ss << in.rdbuf();
    std::string err, ir = lua2gsc::CompileLive(ss.str(), "semantics", &err);
    if (ir.empty()) { std::cerr << err << "\n"; return 1; }
    if (argc > 2) { std::cout << ir << "\n"; return 0; }
    Perk p = Load(ir);
    g_host = std::make_shared<Ent>(); g_host->name = "Host"; g_host->hp = 100;
    g_z1 = std::make_shared<Ent>(); g_z1->name = "z1"; g_z1->hp = 150;
    g_z2 = std::make_shared<Ent>(); g_z2->name = "z2"; g_z2->hp = 150;
    Run(p, 0, {});
    auto info = [&](const char* k) { Val* v = Find(p.rec->f, Name(k)); return v ? *v : Val(); };
    Val c = info("color"), spec = info("specialties"), ms = info("machines");
    char b[64]; snprintf(b, sizeof b, "%g,%g,%g", c.v[0], c.v[1], c.v[2]);
    std::cout << "perk name=" << Text(info("name")) << " cost=" << Text(info("cost")) << " color=" << b << " spec=" << Text(spec.arr->items[0].second)
              << " machines=" << Text(Find(*ms.arr, Name("zm_transit"))->arr->items[0].second) << "\n";
    Run(p, p.handlers["give"], {E(g_host)});
    Val h1 = Run(p, p.handlers["hit"], {E(g_host), E(g_z1), Val::Int(10), Val::Str("MOD_MELEE")});
    Val h2 = Run(p, p.handlers["hit"], {E(g_host), E(g_z1), Val::Int(10), Val::Str("MOD_PISTOL_BULLET")});
    std::cout << "hit " << Text(h1) << " " << Text(h2) << "\n";
    return 0;
}
