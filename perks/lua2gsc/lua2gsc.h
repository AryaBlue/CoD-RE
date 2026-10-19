// lua2gsc - compiles a ZM Workshop perk written in Lua to Plutonium T6 GSC.
//
// One header, C++17, no dependencies. The dialect is a practical subset of Lua 5.1 (see ../API.md):
// locals, functions, if/while/repeat/numeric for/ipairs/pairs, tables as lists or records, string concat,
// plus the perk API (player:give_points(...), zombies_near(...), ...), which maps onto zm_workshop_perks.gsc.
// What GSC can't express is a compile error with a line number, never silently wrong code:
// closures that capture locals, multiple return values, varargs, goto, metatables, coroutines.
//
//   lua2gsc::Result r = lua2gsc::Compile(source, "vampire");
//   if (r.ok) append r.gsc after the runtime, then call r.registerFn from zmwp_register_all().
#pragma once
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace lua2gsc {

struct Result {
    bool ok = false;
    std::string gsc;         // the perk's functions (append after the runtime)
    std::string registerFn;  // e.g. zmwp_vampire_register
    std::string error;       // "line 12: ..." when !ok
    std::string name;        // perk.name, or the id
};

namespace detail {

struct Error : std::runtime_error {
    int line;
    Error(int l, const std::string& m) : std::runtime_error(m), line(l) {}
};

// ---------------------------------------------------------------- lexer
enum TokType { T_EOF, T_NAME, T_NUM, T_STR, T_OP, T_KW };
struct Token { TokType type = T_EOF; std::string text; double num = 0; bool isInt = false; int line = 1; };

static const std::set<std::string> kKeywords = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto",
    "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"};

class Lexer {
public:
    explicit Lexer(const std::string& s) : src(s) {}
    std::vector<Token> Run() {
        std::vector<Token> out;
        for (;;) { Token t = Next(); out.push_back(t); if (t.type == T_EOF) break; }
        return out;
    }
private:
    const std::string& src; size_t p = 0; int line = 1;
    char At(size_t o = 0) const { return p + o < src.size() ? src[p + o] : '\0'; }
    int LongBracket() {   // at '[': returns level of [==[ or -1
        size_t q = p + 1; int level = 0;
        while (q < src.size() && src[q] == '=') { ++level; ++q; }
        return q < src.size() && src[q] == '[' ? level : -1;
    }
    std::string ReadLong(int level) {
        p += level + 2;
        if (At() == '\r') ++p;
        if (At() == '\n') { ++p; ++line; }
        std::string close = "]" + std::string(level, '=') + "]", s;
        for (;;) {
            if (p >= src.size()) throw Error(line, "unfinished long string or comment");
            if (src.compare(p, close.size(), close) == 0) { p += close.size(); return s; }
            if (src[p] == '\n') ++line;
            s += src[p++];
        }
    }
    Token Next() {
        for (;;) {
            while (p < src.size() && (src[p] == ' ' || src[p] == '\t' || src[p] == '\r' || src[p] == '\n')) { if (src[p] == '\n') ++line; ++p; }
            if (At() == '-' && At(1) == '-') {
                p += 2;
                if (At() == '[' && LongBracket() >= 0) { ReadLong(LongBracket()); continue; }
                while (p < src.size() && src[p] != '\n') ++p;
                continue;
            }
            break;
        }
        Token t; t.line = line;
        if (p >= src.size()) return t;
        char c = src[p];
        if (isalpha((unsigned char)c) || c == '_') {
            size_t b = p; while (isalnum((unsigned char)At()) || At() == '_') ++p;
            t.text = src.substr(b, p - b); t.type = kKeywords.count(t.text) ? T_KW : T_NAME; return t;
        }
        if (isdigit((unsigned char)c) || (c == '.' && isdigit((unsigned char)At(1)))) {
            size_t b = p;
            if (c == '0' && (At(1) == 'x' || At(1) == 'X')) {
                p += 2; while (isxdigit((unsigned char)At())) ++p;
                t.num = (double)strtoll(src.substr(b + 2, p - b - 2).c_str(), nullptr, 16); t.isInt = true;
            } else {
                bool isInt = true;
                while (isdigit((unsigned char)At())) ++p;
                if (At() == '.') { isInt = false; ++p; while (isdigit((unsigned char)At())) ++p; }
                if (At() == 'e' || At() == 'E') { isInt = false; ++p; if (At() == '+' || At() == '-') ++p; while (isdigit((unsigned char)At())) ++p; }
                t.num = strtod(src.substr(b, p - b).c_str(), nullptr); t.isInt = isInt;
            }
            t.type = T_NUM; t.text = src.substr(b, p - b); return t;
        }
        if (c == '"' || c == '\'') {
            ++p; std::string s;
            for (;;) {
                if (p >= src.size() || src[p] == '\n') throw Error(line, "unfinished string");
                char d = src[p++];
                if (d == c) break;
                if (d == '\\') {
                    char e = src[p++];
                    switch (e) {
                    case 'n': s += '\n'; break; case 't': s += '\t'; break; case 'r': s += '\r'; break;
                    case '\\': s += '\\'; break; case '"': s += '"'; break; case '\'': s += '\''; break;
                    case '\n': s += '\n'; ++line; break;
                    default: throw Error(line, std::string("unsupported escape \\") + e);
                    }
                } else s += d;
            }
            t.type = T_STR; t.text = s; return t;
        }
        if (c == '[' && LongBracket() >= 0) { t.type = T_STR; t.text = ReadLong(LongBracket()); return t; }
        static const char* ops[] = {"...", "..", "==", "~=", "<=", ">=", "//", "::", "+", "-", "*", "/", "%", "^", "#", "<", ">", "=",
                                    "(", ")", "{", "}", "[", "]", ";", ":", ",", "."};
        for (const char* op : ops) {
            size_t n = strlen(op);
            if (src.compare(p, n, op) == 0) { p += n; t.type = T_OP; t.text = op; return t; }
        }
        throw Error(line, std::string("unexpected character '") + c + "'");
    }
};

// ---------------------------------------------------------------- AST
struct Expr; struct Stat; struct Func;
using ExprP = std::shared_ptr<Expr>; using StatP = std::shared_ptr<Stat>; using FuncP = std::shared_ptr<Func>;
using Block = std::vector<StatP>;

struct Field { ExprP key; std::string name; ExprP value; };   // [key]=v, name=v, or positional (both empty)
struct Expr {
    enum Kind { Nil, True, False, Num, Str, Vararg, Name, Index, Call, Method, Function, Table, Bin, Un, Paren } k;
    int line = 0;
    std::string s;          // Name, Str, op, method name
    double num = 0; bool isInt = false;
    bool dot = false;       // Index written a.name: a record/entity field (a["name"] is a list/map key)
    ExprP a, b;             // Index: a[b]; Bin: a op b; Un: op a; Call/Method: a = callee/object
    std::vector<ExprP> args;
    std::vector<Field> fields;
    FuncP fn;
};
struct Func { std::vector<std::string> params; bool vararg = false; Block body; int line = 0; };
struct Stat {
    enum Kind { Local, Assign, CallS, Do, While, Repeat, If, NumFor, GenFor, FunctionS, LocalFunction, Return, Break } k;
    int line = 0;
    std::vector<std::string> names;      // Local, NumFor/GenFor vars, FunctionS name path
    std::vector<ExprP> targets, exprs;   // Assign targets, values; If conditions; NumFor start/stop/step; GenFor iterators
    std::vector<Block> blocks;           // If: one per condition (+ else); loops/Do: [0]
    ExprP call;                          // CallS; While/Repeat condition
    FuncP fn;
    bool method = false;
};

// ---------------------------------------------------------------- parser
class Parser {
public:
    explicit Parser(std::vector<Token> t) : toks(std::move(t)) {}
    Block Chunk() { Block b = ParseBlock(); if (Cur().type != T_EOF) throw Error(Cur().line, "'" + Cur().text + "' not expected here"); return b; }
private:
    std::vector<Token> toks; size_t i = 0;
    const Token& Cur() const { return toks[i]; }
    const Token& Peek(size_t o = 1) const { return toks[std::min(i + o, toks.size() - 1)]; }
    bool Is(const char* text) const { return (Cur().type == T_OP || Cur().type == T_KW) && Cur().text == text; }
    bool Accept(const char* text) { if (Is(text)) { ++i; return true; } return false; }
    void Expect(const char* text, const char* what) {
        if (!Accept(text)) throw Error(Cur().line, std::string("expected '") + text + "' " + what + (Cur().type == T_EOF ? " (reached the end of the file)" : ", found '" + Cur().text + "'"));
    }
    std::string Name() {
        if (Cur().type != T_NAME) throw Error(Cur().line, "expected a name, found '" + Cur().text + "'");
        return toks[i++].text;
    }
    bool BlockEnd() const { return Cur().type == T_EOF || Is("end") || Is("else") || Is("elseif") || Is("until"); }

    Block ParseBlock() {
        Block b;
        while (!BlockEnd()) {
            if (Accept(";")) continue;
            if (Is("return")) {
                auto s = std::make_shared<Stat>(); s->k = Stat::Return; s->line = Cur().line; ++i;
                if (!BlockEnd() && !Is(";")) s->exprs = ExprList();
                Accept(";");
                b.push_back(s);
                if (!BlockEnd()) throw Error(Cur().line, "'return' must be the last statement of its block");
                break;
            }
            b.push_back(Statement());
        }
        return b;
    }
    StatP Statement() {
        auto s = std::make_shared<Stat>(); s->line = Cur().line;
        if (Accept("break")) { s->k = Stat::Break; return s; }
        if (Is("goto") || Is("::")) throw Error(Cur().line, "goto and labels are not supported (GSC has no goto)");
        if (Accept("do")) { s->k = Stat::Do; s->blocks.push_back(ParseBlock()); Expect("end", "to close 'do'"); return s; }
        if (Accept("while")) {
            s->k = Stat::While; s->call = ParseExpr(); Expect("do", "after the while condition");
            s->blocks.push_back(ParseBlock()); Expect("end", "to close 'while'"); return s;
        }
        if (Accept("repeat")) {
            s->k = Stat::Repeat; s->blocks.push_back(ParseBlock()); Expect("until", "to close 'repeat'"); s->call = ParseExpr(); return s;
        }
        if (Accept("if")) {
            s->k = Stat::If;
            s->exprs.push_back(ParseExpr()); Expect("then", "after the if condition"); s->blocks.push_back(ParseBlock());
            while (Accept("elseif")) { s->exprs.push_back(ParseExpr()); Expect("then", "after the elseif condition"); s->blocks.push_back(ParseBlock()); }
            if (Accept("else")) s->blocks.push_back(ParseBlock());
            Expect("end", "to close 'if'"); return s;
        }
        if (Accept("for")) {
            std::string first = Name();
            if (Accept("=")) {
                s->k = Stat::NumFor; s->names = {first};
                s->exprs.push_back(ParseExpr()); Expect(",", "in the numeric for"); s->exprs.push_back(ParseExpr());
                if (Accept(",")) s->exprs.push_back(ParseExpr());
            } else {
                s->k = Stat::GenFor; s->names = {first};
                while (Accept(",")) s->names.push_back(Name());
                Expect("in", "in the for loop"); s->exprs = ExprList();
            }
            Expect("do", "in the for loop"); s->blocks.push_back(ParseBlock()); Expect("end", "to close 'for'"); return s;
        }
        if (Accept("function")) {
            s->k = Stat::FunctionS; s->names.push_back(Name());
            while (Accept(".")) s->names.push_back(Name());
            if (Accept(":")) { s->names.push_back(Name()); s->method = true; }
            s->fn = Body(s->line); return s;
        }
        if (Accept("local")) {
            if (Accept("function")) { s->k = Stat::LocalFunction; s->names.push_back(Name()); s->fn = Body(s->line); return s; }
            s->k = Stat::Local; s->names.push_back(Name());
            while (Accept(",")) s->names.push_back(Name());
            if (Accept("=")) s->exprs = ExprList();
            return s;
        }
        ExprP e = Suffixed();
        if (Is("=") || Is(",")) {
            s->k = Stat::Assign; s->targets.push_back(e);
            while (Accept(",")) s->targets.push_back(Suffixed());
            Expect("=", "in the assignment");
            s->exprs = ExprList();
            for (auto& t : s->targets) if (t->k != Expr::Name && t->k != Expr::Index) throw Error(s->line, "can't assign to this expression");
            return s;
        }
        if (e->k != Expr::Call && e->k != Expr::Method) throw Error(s->line, "this line does nothing (expected a call or an assignment)");
        s->k = Stat::CallS; s->call = e; return s;
    }
    FuncP Body(int line) {
        auto f = std::make_shared<Func>(); f->line = line;
        Expect("(", "before the parameters");
        if (!Is(")")) {
            do {
                if (Accept("...")) { f->vararg = true; break; }
                f->params.push_back(Name());
            } while (Accept(","));
        }
        Expect(")", "after the parameters");
        f->body = ParseBlock(); Expect("end", "to close the function");
        return f;
    }
    std::vector<ExprP> ExprList() { std::vector<ExprP> v{ParseExpr()}; while (Accept(",")) v.push_back(ParseExpr()); return v; }

    ExprP Primary() {
        auto e = std::make_shared<Expr>(); e->line = Cur().line;
        if (Cur().type == T_NAME) { e->k = Expr::Name; e->s = Name(); return e; }
        if (Accept("(")) { e->k = Expr::Paren; e->a = ParseExpr(); Expect(")", "to close the parenthesis"); return e; }
        throw Error(Cur().line, "unexpected '" + Cur().text + "'");
    }
    ExprP Suffixed() {
        ExprP e = Primary();
        for (;;) {
            int line = Cur().line;
            if (Accept(".")) { auto x = std::make_shared<Expr>(); x->k = Expr::Index; x->line = line; x->a = e; x->dot = true;
                auto key = std::make_shared<Expr>(); key->k = Expr::Str; key->line = line; key->s = Name(); x->b = key; e = x; }
            else if (Accept("[")) { auto x = std::make_shared<Expr>(); x->k = Expr::Index; x->line = line; x->a = e; x->b = ParseExpr(); Expect("]", "to close the index"); e = x; }
            else if (Accept(":")) { auto x = std::make_shared<Expr>(); x->k = Expr::Method; x->line = line; x->a = e; x->s = Name(); x->args = CallArgs(); e = x; }
            else if (Is("(") || Is("{") || Cur().type == T_STR) { auto x = std::make_shared<Expr>(); x->k = Expr::Call; x->line = line; x->a = e; x->args = CallArgs(); e = x; }
            else return e;
        }
    }
    std::vector<ExprP> CallArgs() {
        if (Cur().type == T_STR) { auto s = std::make_shared<Expr>(); s->k = Expr::Str; s->line = Cur().line; s->s = toks[i++].text; return {s}; }
        if (Is("{")) return {TableCons()};
        Expect("(", "for the call");
        std::vector<ExprP> v;
        if (!Is(")")) v = ExprList();
        Expect(")", "to close the call");
        return v;
    }
    ExprP TableCons() {
        auto e = std::make_shared<Expr>(); e->k = Expr::Table; e->line = Cur().line;
        Expect("{", "");
        while (!Is("}")) {
            Field f;
            if (Accept("[")) { f.key = ParseExpr(); Expect("]", "in the table key"); Expect("=", "in the table field"); f.value = ParseExpr(); }
            else if (Cur().type == T_NAME && Peek().type == T_OP && Peek().text == "=") { f.name = Name(); ++i; f.value = ParseExpr(); }
            else f.value = ParseExpr();
            e->fields.push_back(f);
            if (!Accept(",") && !Accept(";")) break;
        }
        Expect("}", "to close the table");
        return e;
    }
    ExprP Simple() {
        auto e = std::make_shared<Expr>(); e->line = Cur().line;
        const Token& t = Cur();
        if (t.type == T_NUM) { e->k = Expr::Num; e->num = t.num; e->isInt = t.isInt; ++i; return e; }
        if (t.type == T_STR) { e->k = Expr::Str; e->s = t.text; ++i; return e; }
        if (Accept("nil")) { e->k = Expr::Nil; return e; }
        if (Accept("true")) { e->k = Expr::True; return e; }
        if (Accept("false")) { e->k = Expr::False; return e; }
        if (Accept("...")) { e->k = Expr::Vararg; return e; }
        if (Is("{")) return TableCons();
        if (Accept("function")) { e->k = Expr::Function; e->fn = Body(e->line); return e; }
        return Suffixed();
    }
    static int LeftPri(const std::string& op) {
        static const std::map<std::string, int> p = {{"or", 1}, {"and", 2}, {"<", 3}, {">", 3}, {"<=", 3}, {">=", 3}, {"~=", 3}, {"==", 3},
            {"..", 9}, {"+", 10}, {"-", 10}, {"*", 11}, {"/", 11}, {"//", 11}, {"%", 11}, {"^", 14}};
        auto it = p.find(op); return it == p.end() ? -1 : it->second;
    }
    static int RightPri(const std::string& op) { return op == ".." ? 8 : op == "^" ? 13 : LeftPri(op); }
    ExprP ParseExpr(int limit = 0) {
        ExprP left;
        if (Is("not") || Is("-") || Is("#")) {
            auto e = std::make_shared<Expr>(); e->k = Expr::Un; e->line = Cur().line; e->s = toks[i++].text; e->a = ParseExpr(12); left = e;
        } else left = Simple();
        for (;;) {
            if (Cur().type != T_OP && Cur().type != T_KW) return left;
            int lp = LeftPri(Cur().text);
            if (lp < 0 || lp <= limit) return left;
            auto e = std::make_shared<Expr>(); e->k = Expr::Bin; e->line = Cur().line; e->s = toks[i++].text;
            e->a = left; e->b = ParseExpr(RightPri(e->s)); left = e;
        }
    }
};

// ---------------------------------------------------------------- code generation
struct ApiFn { const char* gsc; int minArgs, maxArgs; };
static const std::map<std::string, ApiFn>& Globals() {
    static const std::map<std::string, ApiFn> m = {
        {"print", {"zmw_print", 1, 1}}, {"random", {"zmw_random", 1, 2}}, {"random_float", {"zmw_random_float", 2, 2}},
        {"round_number", {"zmw_round_number", 0, 0}}, {"time", {"zmw_time", 0, 0}}, {"players", {"zmw_players", 0, 0}},
        {"zombies", {"zmw_zombies", 0, 0}}, {"zombies_near", {"zmw_zombies_near", 2, 2}}, {"explode", {"zmw_explode", 3, 5}},
        {"play_sound", {"zmw_play_sound", 2, 2}}, {"vector", {"zmw_vector", 3, 3}}, {"tostring", {"zmw_tostring", 1, 1}},
        {"tonumber", {"zmw_tonumber", 1, 1}}, {"distance", {"distance", 2, 2}}, {"abs", {"abs", 1, 1}},
        {"floor", {"floor", 1, 1}}, {"ceil", {"ceil", 1, 1}}, {"sqrt", {"sqrt", 1, 1}}, {"min", {"zmw_min", 2, 2}},
        {"max", {"zmw_max", 2, 2}}};
    return m;
}
static const std::map<std::string, ApiFn>& Library() {   // module.function
    static const std::map<std::string, ApiFn> m = {
        {"math.floor", {"floor", 1, 1}}, {"math.ceil", {"ceil", 1, 1}}, {"math.abs", {"abs", 1, 1}}, {"math.sqrt", {"sqrt", 1, 1}},
        {"math.min", {"zmw_min", 2, 2}}, {"math.max", {"zmw_max", 2, 2}}, {"math.random", {"zmw_random", 1, 2}},
        {"string.lower", {"zmw_lower", 1, 1}}, {"string.sub", {"zmw_sub", 2, 3}}, {"string.find", {"zmw_find", 2, 2}},
        {"table.contains", {"zmw_contains", 2, 2}}};
    return m;
}
static const std::map<std::string, std::pair<int, int>>& Methods() {
    static const std::map<std::string, std::pair<int, int>> m = {
        {"name", {0, 0}}, {"points", {0, 0}}, {"give_points", {1, 1}}, {"take_points", {1, 1}}, {"health", {0, 0}},
        {"set_health", {1, 1}}, {"max_health", {0, 0}}, {"set_max_health", {1, 1}}, {"heal", {0, 0}}, {"origin", {0, 0}},
        {"forward", {0, 0}}, {"distance_to", {1, 1}}, {"is_alive", {0, 0}}, {"is_downed", {0, 0}}, {"revive", {0, 0}},
        {"current_weapon", {0, 0}}, {"give_weapon", {1, 1}}, {"take_weapon", {1, 1}}, {"refill_ammo", {0, 0}},
        {"set_speed", {1, 1}}, {"print", {1, 1}}, {"print_bold", {1, 1}}, {"play_sound", {1, 1}}, {"is_sprinting", {0, 0}},
        {"is_on_ground", {0, 0}}, {"stance", {0, 0}}, {"set_ignored", {1, 1}}, {"damage", {1, 2}}, {"kill", {0, 1}},
        {"has_perk", {1, 1}}, {"give_perk", {1, 1}}, {"take_perk", {1, 1}}, {"shellshock", {2, 2}}};
    return m;
}
// handler function name -> field of the runtime's handler struct, and how many parameters the runtime passes
static const std::map<std::string, std::pair<const char*, int>>& Handlers() {
    static const std::map<std::string, std::pair<const char*, int>> m = {
        {"on_give", {"give", 1}}, {"on_take", {"take", 1}}, {"on_kill", {"kill", 4}}, {"on_hit", {"hit", 5}},
        {"on_damaged", {"damaged", 5}}, {"on_downed", {"downed", 1}}, {"on_revived", {"revived", 1}},
        {"on_round", {"round", 2}}, {"on_tick", {"tick", 1}}};
    return m;
}

static std::string Lower(std::string s) { for (char& c : s) c = (char)tolower((unsigned char)c); return s; }
static std::string Quote(const std::string& s) {
    std::string o = "\"";
    for (char c : s) {
        if (c == '"') o += "\\\""; else if (c == '\\') o += "\\\\"; else if (c == '\n') o += "\\n"; else if (c == '\t') o += "\\t";
        else if (c == '\r') {} else o += c;
    }
    return o + "\"";
}
static std::string NumText(double v, bool isInt) {
    char b[64];
    if (isInt) { snprintf(b, sizeof b, "%lld", (long long)v); return b; }
    snprintf(b, sizeof b, "%.9g", v);
    std::string s = b;
    if (s.find_first_of(".e") == std::string::npos) s += ".0";
    if (s.find('e') != std::string::npos) { snprintf(b, sizeof b, "%.6f", v); s = b; }
    return s;
}

class Gen {
public:
    Gen(const std::string& id) : id(id), prefix("zmwp_" + id + "_") {}
    Result Run(const Block& chunk);
private:
    struct Scope { std::map<std::string, std::string> names; bool fnBoundary = false; };
    std::string id, prefix;
    std::map<std::string, FuncP> functions;          // top-level Lua name -> function
    std::map<std::string, std::string> fnGsc;        // top-level Lua name -> GSC name
    std::set<std::string> usedGsc;                   // lowercase GSC function names in use (GSC ignores case)
    std::set<std::string> usedLocal;                 // lowercase local names of the function being written
    std::vector<Scope> scopes;
    std::vector<std::string>* out = nullptr;         // lines of the function being written
    std::vector<std::string> pending;                // functions written so far
    int indent = 1, temps = 0, anon = 0, loopDepth = 0;
    std::string perkName;

    [[noreturn]] void Fail(int line, const std::string& m) { throw Error(line, m); }
    void Emit(const std::string& l) { out->push_back(std::string(indent * 4, ' ') + l); }
    std::string Temp() { return "_t" + std::to_string(temps++); }
    std::string Unique(const std::string& base) {
        std::string n = base; int k = 2;
        while (usedGsc.count(Lower(n))) n = base + "_" + std::to_string(k++);
        usedGsc.insert(Lower(n));
        return n;
    }
    std::string Declare(const std::string& luaName) {
        std::string base = "v_" + luaName, g = base; int k = 2;
        while (usedLocal.count(Lower(g))) g = base + "_" + std::to_string(k++);
        usedLocal.insert(Lower(g));
        scopes.back().names[luaName] = g;
        return g;
    }
    // GSC name of a Lua local, "" if it isn't one. Locals of an enclosing function can't be reached (no closures).
    std::string Local(const std::string& n, int line) {
        bool crossed = false;
        for (size_t s = scopes.size(); s-- > 0;) {
            auto it = scopes[s].names.find(n);
            if (it != scopes[s].names.end()) {
                if (crossed) Fail(line, "'" + n + "' is a local of the enclosing function; GSC functions can't capture locals - pass it as an argument or make it a perk global");
                return it->second;
            }
            if (scopes[s].fnBoundary) crossed = true;
        }
        return "";
    }
    std::string GlobalRef(const std::string& n) { return "level." + prefix + "g_" + Lower(n); }

    std::string Val(const ExprP& e, std::vector<std::string>& pre);
    std::string Cond(const ExprP& e, std::vector<std::string>& pre);
    std::string CallExpr(const ExprP& e, std::vector<std::string>& pre, bool statement);
    std::string Index(const ExprP& e, std::vector<std::string>& pre);
    std::string Simple(const ExprP& e, std::vector<std::string>& pre) {   // evaluate once; hoist anything with side effects
        std::string v = Val(e, pre);
        if (e->k == Expr::Name || e->k == Expr::Num || e->k == Expr::Str || e->k == Expr::Nil || e->k == Expr::True || e->k == Expr::False) return v;
        std::string t = Temp(); pre.push_back(t + " = " + v + ";"); return t;
    }
    std::vector<std::string> Args(const std::vector<ExprP>& args, std::vector<std::string>& pre, int line) {
        std::vector<std::string> v;
        for (auto& a : args) { if (a->k == Expr::Vararg) Fail(line, "'...' is not supported"); v.push_back(Val(a, pre)); }
        return v;
    }
    static std::string Join(const std::vector<std::string>& v) {
        std::string s; for (size_t i = 0; i < v.size(); ++i) s += (i ? ", " : "") + v[i];
        return v.empty() ? "()" : "( " + s + " )";
    }
    void Flush(std::vector<std::string>& pre) { for (auto& l : pre) Emit(l); pre.clear(); }
    void BlockOut(const Block& b, bool newScope = true);
    void StatOut(const StatP& s);
    std::string FunctionOut(const FuncP& f, const std::string& gscName, int line, bool boundary);
    std::string ConstVal(const ExprP& e, const std::string& what);
};

std::string Gen::ConstVal(const ExprP& e, const std::string& what) {
    switch (e->k) {
    case Expr::Num: return NumText(e->num, e->isInt);
    case Expr::Str: return Quote(e->s);
    case Expr::True: return "1";
    case Expr::False: return "0";
    case Expr::Un: if (e->s == "-" && e->a->k == Expr::Num) return "-" + NumText(e->a->num, e->a->isInt); break;
    default: break;
    }
    Fail(e->line, what + " must be a plain number or string");
}

std::string Gen::Index(const ExprP& e, std::vector<std::string>& pre) {
    std::string obj = Val(e->a, pre);
    const ExprP& key = e->b;
    // a.name is a field of a record ({ name = ... }) or entity (player.kills); a["name"] is a key of a list/map
    if (e->dot) return obj + "." + Lower(key->s);
    if (key->k == Expr::Str) return obj + "[" + Quote(key->s) + "]";
    if (key->k == Expr::Num && key->isInt) return obj + "[" + std::to_string((long long)key->num - 1) + "]";
    return obj + "[zmw_idx( " + Val(key, pre) + " )]";
}

std::string Gen::CallExpr(const ExprP& e, std::vector<std::string>& pre, bool statement) {
    int line = e->line;
    if (e->k == Expr::Method) {
        auto it = Methods().find(e->s);
        if (it == Methods().end()) Fail(line, "unknown method ':" + e->s + "' (see API.md for player and zombie methods)");
        int n = (int)e->args.size();
        if (n < it->second.first || n > it->second.second) Fail(line, ":" + e->s + " takes " + std::to_string(it->second.first) +
            (it->second.first != it->second.second ? "-" + std::to_string(it->second.second) : "") + " argument(s)");
        std::vector<std::string> args{Simple(e->a, pre)};
        for (auto& a : Args(e->args, pre, line)) args.push_back(a);
        return "zmwa_" + e->s + Join(args);
    }
    const ExprP& callee = e->a;
    std::vector<std::string> args;
    if (callee->k == Expr::Name) {
        const std::string& n = callee->s;
        std::string local = Local(n, line);
        if (!local.empty()) return "[[ " + local + " ]]" + Join(Args(e->args, pre, line));
        if (functions.count(n)) {
            const FuncP& f = functions[n];
            if (e->args.size() > f->params.size()) Fail(line, n + " takes " + std::to_string(f->params.size()) + " argument(s)");
            return fnGsc[n] + Join(Args(e->args, pre, line));
        }
        if (n == "wait") {
            if (!statement) Fail(line, "wait() can only be used as a statement");
            if (e->args.size() != 1) Fail(line, "wait takes one argument (seconds)");
            return "wait( " + Val(e->args[0], pre) + " )";
        }
        if (n == "thread") {
            if (!statement) Fail(line, "thread() can only be used as a statement");
            if (e->args.empty() || e->args[0]->k != Expr::Name || !functions.count(e->args[0]->s))
                Fail(line, "thread(f, ...) needs one of this perk's functions as f");
            std::vector<ExprP> rest(e->args.begin() + 1, e->args.end());
            return "level thread " + fnGsc[e->args[0]->s] + Join(Args(rest, pre, line));
        }
        if (n == "ipairs" || n == "pairs") Fail(line, n + " can only be used in a for loop");
        auto g = Globals().find(n);
        if (g == Globals().end()) Fail(line, "unknown function '" + n + "' (not defined in this perk or the API)");
        int c = (int)e->args.size();
        if (c < g->second.minArgs || c > g->second.maxArgs) Fail(line, n + " takes " + std::to_string(g->second.minArgs) +
            (g->second.minArgs != g->second.maxArgs ? "-" + std::to_string(g->second.maxArgs) : "") + " argument(s)");
        return std::string(g->second.gsc) + Join(Args(e->args, pre, line));
    }
    if (callee->k == Expr::Index && callee->a->k == Expr::Name && callee->b->k == Expr::Str && Local(callee->a->s, line).empty()) {
        std::string full = callee->a->s + "." + callee->b->s;
        if (full == "table.insert") {
            if (!statement || e->args.size() != 2) Fail(line, "table.insert(t, value) must be a statement with two arguments");
            std::string t = Val(e->args[0], pre);
            return t + "[" + t + ".size] = " + Val(e->args[1], pre);
        }
        if (full == "table.remove") {
            if (!statement || e->args.size() != 2) Fail(line, "table.remove(t, i) must be a statement with two arguments");
            std::string t = Val(e->args[0], pre);
            return t + " = zmw_remove( " + t + ", " + Val(e->args[1], pre) + " )";
        }
        auto g = Library().find(full);
        if (g != Library().end()) {
            int c = (int)e->args.size();
            if (c < g->second.minArgs || c > g->second.maxArgs) Fail(line, full + ": wrong number of arguments");
            return std::string(g->second.gsc) + Join(Args(e->args, pre, line));
        }
        if (callee->a->s == "math" || callee->a->s == "string" || callee->a->s == "table" || callee->a->s == "os" || callee->a->s == "io")
            Fail(line, full + " is not available (see API.md)");
    }
    // a function stored in a variable or table field
    return "[[ " + Val(callee, pre) + " ]]" + Join(Args(e->args, pre, line));
}

std::string Gen::Val(const ExprP& e, std::vector<std::string>& pre) {
    switch (e->k) {
    case Expr::Nil: return "undefined";
    case Expr::True: return "1";
    case Expr::False: return "0";
    case Expr::Num: return NumText(e->num, e->isInt);
    case Expr::Str: return Quote(e->s);
    case Expr::Vararg: Fail(e->line, "'...' is not supported");
    case Expr::Paren: return "( " + Val(e->a, pre) + " )";
    case Expr::Name: {
        std::string l = Local(e->s, e->line);
        if (!l.empty()) return l;
        if (functions.count(e->s)) return "::" + fnGsc[e->s];
        if (e->s == "perk") return "level.zmwp[" + Quote(id) + "]";
        if (Globals().count(e->s) || e->s == "wait" || e->s == "thread") Fail(e->line, "'" + e->s + "' is an API function; call it, e.g. " + e->s + "(...)");
        if (e->s == "math" || e->s == "string" || e->s == "table") Fail(e->line, "'" + e->s + "' can only be used as " + e->s + ".function(...)");
        return GlobalRef(e->s);
    }
    case Expr::Index: return Index(e, pre);
    case Expr::Call: case Expr::Method: return CallExpr(e, pre, false);
    case Expr::Function: {
        std::string name = Unique(prefix + "fn" + std::to_string(++anon));
        std::vector<std::string>* saved = out; int savedIndent = indent, savedTemps = temps;
        FunctionOut(e->fn, name, e->line, true);
        out = saved; indent = savedIndent; temps = savedTemps;
        return "::" + name;
    }
    case Expr::Table: {
        bool record = !e->fields.empty();
        for (auto& f : e->fields) record = record && !f.name.empty();
        std::string t = Temp();
        std::vector<std::string> body;
        pre.push_back(t + (record ? " = spawnstruct();" : " = [];"));
        int pos = 0;
        for (auto& f : e->fields) {
            std::string v = Val(f.value, pre);
            if (!f.name.empty()) pre.push_back(record ? t + "." + Lower(f.name) + " = " + v + ";" : t + "[" + Quote(f.name) + "] = " + v + ";");
            else if (f.key) {
                if (f.key->k == Expr::Num && f.key->isInt) pre.push_back(t + "[" + std::to_string((long long)f.key->num - 1) + "] = " + v + ";");
                else pre.push_back(t + "[zmw_idx( " + Val(f.key, pre) + " )] = " + v + ";");
            } else pre.push_back(t + "[" + std::to_string(pos++) + "] = " + v + ";");
        }
        return t;
    }
    case Expr::Un: {
        if (e->s == "not") return "!" + Cond(e->a, pre);
        if (e->s == "#") return Val(e->a, pre) + ".size";
        if (e->a->k == Expr::Num) return "-" + NumText(e->a->num, e->a->isInt);
        return "( 0 - " + Val(e->a, pre) + " )";
    }
    case Expr::Bin: {
        const std::string& op = e->s;
        if (op == "and" || op == "or") {
            std::string a = Simple(e->a, pre);
            std::vector<std::string> bpre;
            std::string b = Val(e->b, bpre);
            if (!bpre.empty()) {   // b needs setup lines: only run them when b is used
                std::string t = Temp();
                pre.push_back(t + " = " + a + ";");
                pre.push_back(std::string("if ( ") + (op == "or" ? "!" : "") + "zmw_truthy( " + t + " ) )");
                pre.push_back("{");
                for (auto& l : bpre) pre.push_back("    " + l);
                pre.push_back("    " + t + " = " + b + ";");
                pre.push_back("}");
                return t;
            }
            return op == "or" ? "( zmw_truthy( " + a + " ) ? " + a + " : " + b + " )" : "( zmw_truthy( " + a + " ) ? " + b + " : " + a + " )";
        }
        if (op == "==" || op == "~=") {
            bool eq = op == "==";
            if (e->b->k == Expr::Nil) return std::string(eq ? "!" : "") + "isdefined( " + Val(e->a, pre) + " )";
            if (e->a->k == Expr::Nil) return std::string(eq ? "!" : "") + "isdefined( " + Val(e->b, pre) + " )";
            // GSC stops the script when comparing undefined or mismatched types; Lua just says false
            return std::string(eq ? "" : "!") + "zmw_eq( " + Val(e->a, pre) + ", " + Val(e->b, pre) + " )";
        }
        if (op == "..") {
            // flatten a .. b .. c; "" first so numbers join as text (GSC + would add them)
            std::vector<ExprP> parts; std::vector<ExprP> stack{e};
            while (!stack.empty()) {
                ExprP x = stack.back(); stack.pop_back();
                if (x->k == Expr::Bin && x->s == "..") { stack.push_back(x->b); stack.push_back(x->a); } else parts.push_back(x);
            }
            std::string s = parts[0]->k == Expr::Str ? "" : "\"\" + ";
            for (size_t i = 0; i < parts.size(); ++i) s += (i ? " + " : "") + Val(parts[i], pre);
            return "( " + s + " )";
        }
        std::string a = Val(e->a, pre), b = Val(e->b, pre);
        if (op == "/") return "( " + a + " * 1.0 / " + b + " )";
        if (op == "//") return "zmw_floordiv( " + a + ", " + b + " )";
        if (op == "^") return "zmw_pow( " + a + ", " + b + " )";
        return "( " + a + " " + op + " " + b + " )";
    }
    }
    Fail(e->line, "unsupported expression");
}

std::string Gen::Cond(const ExprP& e, std::vector<std::string>& pre) {
    if (e->k == Expr::True) return "1";
    if (e->k == Expr::False || e->k == Expr::Nil) return "0";
    if (e->k == Expr::Paren) return Cond(e->a, pre);
    if (e->k == Expr::Un && e->s == "not") return "!" + Cond(e->a, pre);
    if (e->k == Expr::Bin) {
        if (e->s == "and" || e->s == "or") {
            std::vector<std::string> bpre;
            std::string a = Cond(e->a, pre), b = Cond(e->b, bpre);
            if (!bpre.empty()) {   // keep short-circuit: b's setup runs only when needed
                std::string t = Temp();
                pre.push_back(t + " = " + a + ";");
                pre.push_back(std::string("if ( ") + (e->s == "and" ? "" : "!") + t + " )");
                pre.push_back("{");
                for (auto& l : bpre) pre.push_back("    " + l);
                pre.push_back("    " + t + " = " + b + ";");
                pre.push_back("}");
                return t;
            }
            return "( " + a + (e->s == "and" ? " && " : " || ") + b + " )";
        }
        static const std::set<std::string> cmp = {"==", "~=", "<", ">", "<=", ">="};
        if (cmp.count(e->s)) return Val(e, pre);
    }
    return "zmw_truthy( " + Val(e, pre) + " )";
}

void Gen::BlockOut(const Block& b, bool newScope) {
    if (newScope) scopes.push_back({});
    for (auto& s : b) StatOut(s);
    if (newScope) scopes.pop_back();
}

void Gen::StatOut(const StatP& s) {
    std::vector<std::string> pre;
    switch (s->k) {
    case Stat::Local: {
        std::vector<std::string> vals;
        for (size_t i = 0; i < s->names.size(); ++i) {
            if (i < s->exprs.size()) vals.push_back(Val(s->exprs[i], pre));
            else vals.push_back("undefined");
        }
        if (s->exprs.size() > s->names.size()) Fail(s->line, "more values than names");
        if (s->names.size() > 1 && s->exprs.size() == 1 && (s->exprs[0]->k == Expr::Call || s->exprs[0]->k == Expr::Method))
            Fail(s->line, "functions return one value in GSC; assign each name separately");
        Flush(pre);
        // declare after evaluating: `local x = x` reads the outer x
        for (size_t i = 0; i < s->names.size(); ++i) Emit(Declare(s->names[i]) + " = " + vals[i] + ";");
        break;
    }
    case Stat::Assign: {
        if (s->exprs.size() != s->targets.size()) Fail(s->line, "give every name in the assignment its own value");
        if (s->targets.size() == 1) {
            std::string v = Val(s->exprs[0], pre), t = Val(s->targets[0], pre);
            Flush(pre); Emit(t + " = " + v + ";");
        } else {
            std::vector<std::string> temps;
            for (auto& x : s->exprs) { std::string t = Temp(); pre.push_back(t + " = " + Val(x, pre) + ";"); temps.push_back(t); }
            for (size_t i = 0; i < s->targets.size(); ++i) pre.push_back(Val(s->targets[i], pre) + " = " + temps[i] + ";");
            Flush(pre);
        }
        break;
    }
    case Stat::CallS: { std::string c = CallExpr(s->call, pre, true); Flush(pre); Emit(c + ";"); break; }
    case Stat::Do: Emit("{"); ++indent; BlockOut(s->blocks[0]); --indent; Emit("}"); break;
    case Stat::While: {
        std::string c = Cond(s->call, pre);
        if (!pre.empty()) {   // condition needs setup: evaluate it at the top of each pass
            Emit("while ( true )"); Emit("{"); ++indent; Flush(pre); Emit("if ( !( " + c + " ) )"); Emit("    break;");
        } else { Emit("while ( " + c + " )"); Emit("{"); ++indent; }
        ++loopDepth; BlockOut(s->blocks[0]); --loopDepth; --indent; Emit("}");
        break;
    }
    case Stat::Repeat: {
        Emit("while ( true )"); Emit("{"); ++indent; ++loopDepth;
        scopes.push_back({});                       // `until` sees the body's locals
        for (auto& x : s->blocks[0]) StatOut(x);
        std::string c = Cond(s->call, pre); Flush(pre);
        scopes.pop_back();
        Emit("if ( " + c + " )"); Emit("    break;");
        --loopDepth; --indent; Emit("}");
        break;
    }
    case Stat::If: {
        // elseif conditions may need setup lines, so each one opens a nested else block
        int opened = 0;
        for (size_t i = 0; i < s->exprs.size(); ++i) {
            std::string c = Cond(s->exprs[i], pre); Flush(pre);
            Emit("if ( " + c + " )"); Emit("{"); ++indent; BlockOut(s->blocks[i]); --indent; Emit("}");
            if (i + 1 < s->blocks.size()) { Emit("else"); Emit("{"); ++indent; ++opened; }
        }
        if (s->blocks.size() > s->exprs.size()) BlockOut(s->blocks.back());
        while (opened--) { --indent; Emit("}"); }
        break;
    }
    case Stat::NumFor: {
        std::string start = Val(s->exprs[0], pre), stop = Simple(s->exprs[1], pre);
        std::string step = "1"; bool down = false;
        if (s->exprs.size() > 2) {
            const ExprP& st = s->exprs[2];
            if (st->k == Expr::Num) step = NumText(st->num, st->isInt);
            else if (st->k == Expr::Un && st->s == "-" && st->a->k == Expr::Num) { step = "-" + NumText(st->a->num, st->a->isInt); down = true; }
            else Fail(s->line, "the for loop step must be a number written in the code (e.g. 2 or -1)");
        }
        Flush(pre);
        scopes.push_back({});
        std::string v = Declare(s->names[0]);
        Emit("for ( " + v + " = " + start + "; " + v + (down ? " >= " : " <= ") + stop + "; " + v + " += " + step + " )");
        Emit("{"); ++indent; ++loopDepth; BlockOut(s->blocks[0]); --loopDepth; --indent; Emit("}");
        scopes.pop_back();
        break;
    }
    case Stat::GenFor: {
        if (s->exprs.size() != 1 || s->exprs[0]->k != Expr::Call || s->exprs[0]->a->k != Expr::Name ||
            (s->exprs[0]->a->s != "ipairs" && s->exprs[0]->a->s != "pairs") || s->exprs[0]->args.size() != 1)
            Fail(s->line, "for ... in only works with ipairs(t) or pairs(t)");
        bool ip = s->exprs[0]->a->s == "ipairs";
        if (s->names.size() > 2) Fail(s->line, "ipairs/pairs give two values (key, value)");
        std::string t = Temp(), i = Temp();
        pre.push_back(t + " = " + Val(s->exprs[0]->args[0], pre) + ";");
        std::string keys;
        if (!ip) { keys = Temp(); pre.push_back(keys + " = getarraykeys( " + t + " );"); }
        Flush(pre);
        scopes.push_back({});
        Emit("for ( " + i + " = 0; " + i + " < " + (ip ? t : keys) + ".size; " + i + "++ )");
        Emit("{"); ++indent;
        std::string k = Declare(s->names[0]);
        if (ip) Emit(k + " = " + i + " + 1;"); else Emit(k + " = zmw_key_out( " + keys + "[" + i + "] );");
        if (s->names.size() > 1) Emit(Declare(s->names[1]) + " = " + t + "[" + (ip ? i : keys + "[" + i + "]") + "];");
        ++loopDepth; BlockOut(s->blocks[0]); --loopDepth;
        --indent; Emit("}");
        scopes.pop_back();
        break;
    }
    case Stat::FunctionS: case Stat::LocalFunction:
        Fail(s->line, "functions must be defined at the top level of the perk file (GSC has no nested functions)");
    case Stat::Return: {
        if (s->exprs.size() > 1) Fail(s->line, "GSC functions return one value");
        if (s->exprs.empty()) { Emit("return;"); break; }
        std::string v = Val(s->exprs[0], pre); Flush(pre); Emit("return " + v + ";");
        break;
    }
    case Stat::Break:
        if (!loopDepth) Fail(s->line, "'break' outside a loop");
        Emit("break;");
        break;
    }
}

std::string Gen::FunctionOut(const FuncP& f, const std::string& gscName, int line, bool boundary) {
    if (f->vararg) Fail(line, "'...' parameters are not supported");
    std::vector<std::string> lines;
    std::set<std::string> savedLocals = usedLocal;
    usedLocal.clear();
    out = &lines; indent = 1; temps = 0;
    Scope sc; sc.fnBoundary = boundary;
    scopes.push_back(sc);
    std::vector<std::string> params;
    for (auto& p : f->params) params.push_back(Declare(p));
    int savedLoop = loopDepth; loopDepth = 0;
    BlockOut(f->body, false);
    loopDepth = savedLoop;
    scopes.pop_back();
    std::string text = gscName + Join(params) + "\n{\n";
    for (auto& l : lines) text += l + "\n";
    text += "}\n";
    pending.push_back(text);
    usedLocal = savedLocals;
    return text;
}

Result Gen::Run(const Block& chunk) {
    Result r;
    usedGsc.insert(Lower(prefix + "register"));
    // pass 1: collect top-level functions and the perk table
    ExprP perkTable;
    std::vector<StatP> globals;
    for (auto& s : chunk) {
        if (s->k == Stat::FunctionS || s->k == Stat::LocalFunction) {
            if (s->names.size() != 1) Fail(s->line, "define plain functions (function name(...)); tables of functions are not supported");
            if (functions.count(s->names[0])) Fail(s->line, "function '" + s->names[0] + "' is defined twice");
            functions[s->names[0]] = s->fn;
            fnGsc[s->names[0]] = Unique(prefix + Lower(s->names[0]));
        } else if (s->k == Stat::Assign && s->targets.size() == 1 && s->targets[0]->k == Expr::Name && s->targets[0]->s == "perk") {
            if (s->exprs[0]->k != Expr::Table) Fail(s->line, "perk must be a table: perk = { name = \"...\", cost = 2500, ... }");
            perkTable = s->exprs[0];
        } else if (s->k == Stat::Local || s->k == Stat::Assign) globals.push_back(s);
        else Fail(s->line, "only definitions belong at the top level of a perk; put code inside on_give, on_kill, ...");
    }
    if (!perkTable) Fail(1, "the perk needs a table: perk = { name = \"My Perk\", cost = 2500 }");
    for (auto& [name, f] : functions) {
        auto h = Handlers().find(name);
        if (h != Handlers().end() && (int)f->params.size() > h->second.second)
            Fail(f->line, name + " gets " + std::to_string(h->second.second) + " argument(s); it has " + std::to_string(f->params.size()));
    }
    // pass 2: functions
    for (auto& [name, f] : functions) {
        // the runtime passes a fixed number of arguments; pad so GSC is never called with more than it declares
        auto h = Handlers().find(name);
        FuncP g = f;
        if (h != Handlers().end() && (int)f->params.size() < h->second.second) {
            g = std::make_shared<Func>(*f);
            while ((int)g->params.size() < h->second.second) g->params.push_back("_unused" + std::to_string(g->params.size()));
        }
        FunctionOut(g, fnGsc[name], f->line, false);
    }
    // register: the perk table, globals' first values, handlers
    std::vector<std::string> lines;
    out = &lines; indent = 1; temps = 0;
    scopes.push_back({});
    Emit("info = spawnstruct();");
    Emit("info.id = " + Quote(id) + ";");
    double tickEvery = 0;
    for (auto& fld : perkTable->fields) {
        if (fld.name.empty()) Fail(perkTable->line, "perk fields need names (name = ..., cost = ...)");
        const std::string& n = fld.name;
        if (n == "color") {
            if (fld.value->k != Expr::Table || fld.value->fields.size() != 3) Fail(fld.value->line, "color = { r, g, b } with values 0-1");
            std::vector<std::string> c;
            for (auto& x : fld.value->fields) c.push_back(ConstVal(x.value, "each color value"));
            Emit("info.color = ( " + c[0] + ", " + c[1] + ", " + c[2] + " );");
        } else if (n == "machines") {
            if (fld.value->k != Expr::Table) Fail(fld.value->line, "machines = { zm_transit = { \"x y z yaw\", ... } }");
            Emit("info.machines = [];");
            for (auto& m : fld.value->fields) {
                if (m.name.empty() || m.value->k != Expr::Table) Fail(fld.value->line, "machines = { mapname = { \"x y z yaw\", ... } }");
                Emit("info.machines[" + Quote(m.name) + "] = [];");
                int k = 0;
                for (auto& spot : m.value->fields) {
                    if (spot.value->k != Expr::Str) Fail(spot.value->line, "each machine spot is a string \"x y z yaw\"");
                    Emit("info.machines[" + Quote(m.name) + "][" + std::to_string(k++) + "] = " + Quote(spot.value->s) + ";");
                }
            }
        } else if (n == "tick_every") {
            if (fld.value->k != Expr::Num) Fail(fld.value->line, "tick_every is a number of seconds");
            tickEvery = fld.value->num;
        } else if (n == "name" || n == "hint" || n == "icon" || n == "machine" || n == "bottle" || n == "description") {
            if (fld.value->k != Expr::Str) Fail(fld.value->line, n + " must be a string");
            if (n == "name") perkName = fld.value->s;
            Emit("info." + n + " = " + Quote(fld.value->s) + ";");
        } else if (n == "cost") {
            Emit("info.cost = " + ConstVal(fld.value, "cost") + ";");
        } else Fail(fld.value->line, "unknown perk field '" + n + "' (name, description, cost, hint, icon, color, machine, bottle, machines, tick_every)");
    }
    std::vector<std::string> pre;
    for (auto& s : globals) {
        if (s->k == Stat::Assign && s->targets.size() == 1 && s->targets[0]->k == Expr::Name) {
            std::string v = Val(s->exprs[0], pre); Flush(pre);
            Emit(GlobalRef(s->targets[0]->s) + " = " + v + ";");
        } else if (s->k == Stat::Local) {   // a top-level local is a perk global too (every function can see it)
            for (size_t i = 0; i < s->names.size(); ++i) {
                std::string v = i < s->exprs.size() ? Val(s->exprs[i], pre) : "undefined"; Flush(pre);
                Emit(GlobalRef(s->names[i]) + " = " + v + ";");
            }
        } else Fail(s->line, "top-level assignments set one global at a time");
    }
    Emit("h = spawnstruct();");
    for (auto& [lua, hf] : Handlers()) if (functions.count(lua)) Emit("h." + std::string(hf.first) + " = ::" + fnGsc[lua] + ";");
    if (tickEvery > 0) Emit("h.tick_every = " + NumText(tickEvery, false) + ";");
    Emit("zmwp_add( info, h );");
    scopes.pop_back();
    r.registerFn = prefix + "register";
    std::string reg = r.registerFn + "()\n{\n";
    for (auto& l : lines) reg += l + "\n";
    reg += "}\n";
    r.gsc = "// ---- perk " + id + (perkName.empty() ? "" : " (" + perkName + ")") + " - compiled from Lua by lua2gsc\n\n" + reg;
    for (auto& p : pending) r.gsc += "\n" + p;
    r.name = perkName.empty() ? id : perkName;
    r.ok = true;
    return r;
}

}  // namespace detail

// id: the perk's id ([a-z0-9_], used in GSC names and by the tool's give/take commands)
inline Result Compile(const std::string& source, const std::string& rawId) {
    Result r;
    std::string id;
    for (char c : rawId) id += isalnum((unsigned char)c) ? (char)tolower((unsigned char)c) : '_';
    if (id.empty() || isdigit((unsigned char)id[0])) id = "p" + id;
    try {
        detail::Lexer lx(source);
        detail::Parser ps(lx.Run());
        detail::Block chunk = ps.Chunk();
        detail::Gen g(id);
        return g.Run(chunk);
    } catch (const detail::Error& e) {
        r.error = "line " + std::to_string(e.line) + ": " + e.what();
    }
    return r;
}

// The whole script for Plutonium: runtime, every compiled perk, and the function that registers them.
inline std::string Bundle(const std::string& runtime, const std::vector<Result>& perks) {
    std::string s = runtime;
    for (auto& p : perks) if (p.ok) s += "\n" + p.gsc;
    s += "\nzmwp_register_all()\n{\n";
    for (auto& p : perks) if (p.ok) s += "    " + p.registerFn + "();\n";
    s += "}\n";
    return s;
}

}  // namespace lua2gsc
