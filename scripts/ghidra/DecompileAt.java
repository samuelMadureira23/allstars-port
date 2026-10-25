// Decompile the functions containing the given addresses and write one .c file per
// function into an output directory.
// Headless args: <outDir> <addr> [addr ...]
//@category ps3port
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

import java.io.File;
import java.io.PrintWriter;

public class DecompileAt extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args[0]);
        out.mkdirs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (int i = 1; i < args.length; i++) {
            Address a = toAddr(args[i]);
            Function f = getFunctionContaining(a);
            if (f == null) {
                disassemble(a);
                f = createFunction(a, null);
            }
            if (f == null) {
                println("no function at " + args[i]);
                continue;
            }
            DecompileResults r = di.decompileFunction(f, 120, monitor);
            String name = String.format("%08x_%s.c", f.getEntryPoint().getOffset(), f.getName());
            try (PrintWriter w = new PrintWriter(new File(out, name), "UTF-8")) {
                w.println("// " + f.getName() + " @ " + f.getEntryPoint() + "  body=" + f.getBody());
                w.println(r.decompileCompleted() ? r.getDecompiledFunction().getC() : "// FAILED: " + r.getErrorMessage());
            }
            println("wrote " + name);
        }
        di.dispose();
    }
}
