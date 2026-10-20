// Decompile functions by name or hex address. Args: <outfile> <name|0xaddr>...
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;

public class Decomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        PrintWriter out = new PrintWriter(new OutputStreamWriter(new FileOutputStream(args[0], true), "UTF-8"));
        DecompInterface d = new DecompInterface();
        DecompileOptions o = new DecompileOptions();
        d.setOptions(o);
        d.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        for (int i = 1; i < args.length; i++) {
            List<Function> fs = new ArrayList<>();
            String a = args[i];
            if (a.startsWith("0x")) {
                Address ad = toAddr(Long.parseLong(a.substring(2), 16));
                Function f = fm.getFunctionAt(ad);
                if (f == null) f = fm.getFunctionContaining(ad);
                if (f == null) { disassemble(ad); f = createFunction(ad, null); }
                if (f != null) fs.add(f);
            } else {
                for (Symbol s : currentProgram.getSymbolTable().getSymbols(a)) {
                    Function f = fm.getFunctionAt(s.getAddress());
                    if (f != null) fs.add(f);
                }
                if (fs.isEmpty()) {
                    for (Function f : fm.getFunctions(true)) if (f.getName().equals(a)) fs.add(f);
                }
            }
            if (fs.isEmpty()) { out.println("// NOT FOUND " + a); continue; }
            for (Function f : fs) {
                DecompileResults r = d.decompileFunction(f, 120, monitor);
                out.println("// ===== " + f.getName() + " @ " + f.getEntryPoint());
                out.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// FAILED " + r.getErrorMessage());
            }
        }
        out.close();
        d.dispose();
    }
}
