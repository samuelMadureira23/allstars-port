// Export bounded static observations after headless analysis.
// @category AllStarPort
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.PrintWriter;
import java.io.File;

public class ExportSummary extends GhidraScript {
    public void run() throws Exception {
        File directory = new File(getScriptArgs()[0]);
        directory.mkdirs();
        try (PrintWriter out = new PrintWriter(new File(directory, "ghidra-summary.txt"), "UTF-8")) {
            out.println("Method: direct Ghidra static analysis; not REA Evidence and not original source.");
            out.println("Program: " + currentProgram.getName());
            out.println("SHA256: " + currentProgram.getExecutableSHA256());
            out.println("Language: " + currentProgram.getLanguageID());
            out.println("Compiler: " + currentProgram.getCompilerSpec().getCompilerSpecID());
            out.println("Functions: " + currentProgram.getFunctionManager().getFunctionCount());
            out.println("NOTE: generic ELF loader; PS3 ABI/import names require independent validation.");
            for (var block : currentProgram.getMemory().getBlocks()) {
                out.println("Block " + block.getName() + " " + block.getStart() + " size=" + block.getSize());
            }
        }
        DecompInterface decompiler = new DecompInterface();
        try (PrintWriter functions = new PrintWriter(new File(directory, "functions.tsv"), "UTF-8");
             PrintWriter sample = new PrintWriter(new File(directory, "sample-pseudocode.c"), "UTF-8")) {
            functions.println("address\tname\tbody_bytes");
            decompiler.openProgram(currentProgram);
            FunctionIterator iterator = currentProgram.getFunctionManager().getFunctions(true);
            int exported = 0;
            sample.println("/* Exploratory Ghidra pseudocode. Not original source; not a compilable PC port. */");
            while (iterator.hasNext() && !monitor.isCancelled()) {
                Function function = iterator.next();
                long length = function.getBody().getNumAddresses();
                functions.println(function.getEntryPoint() + "\t" + function.getName() + "\t" + length);
                if (exported < 3 && length >= 24 && length <= 256 && !function.isExternal() && !function.isThunk()) {
                    DecompileResults result = decompiler.decompileFunction(function, 15, monitor);
                    if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                        sample.println("/* Address: " + function.getEntryPoint() + " */");
                        sample.println(result.getDecompiledFunction().getC());
                        exported++;
                    }
                }
            }
        } finally { decompiler.dispose(); }
    }
}
