# RISC-V_processor_simulator
The repository contains the project of ECE6913-Computer System & architecture of NYU Tandon School
# Introduce
This project implement cycle-accurate simulators of a 32-bit RISC-V processor in Python.

**The simulators take in two files as inputs: imem.text and dmem.txt files**
The simulator give out the following:
- cycle by cycle state of the register file (RFOutput.txt)
- Cycle by cycle microarchitectural state of the machine (StateResult. txt)
- Resulting dmem data after the execution of the program (DmemResult.txt)

The imem. txt file is used to initialize the instruction memory and the dmem.txt file is used to initialize the data memory of the processor. Each line in the files contain a byte of data on the instruction or the data memory and both the instruction and data memory are byte addressable. This means that for a 32 bit processor, 4 lines in the imem.txt file makes one instruction. Both instruction and data memory are in "Big-Endian" format (the most significant byte is stored in the smallest address).

**The simulator have the following five stages in its pipeline:**
- Instruction Fetch: Fetches instruction from the instruction memory using PC value as address.
- Instruction Decode/ Register Read: Decodes the instruction using the format in the table above and generates control signals and data signals after reading from the register file.
- Execute: Perform operations on the data as directed by the control signals.
- Load/ Store: Perform memory related operations.
- Writeback: Write the result back into the destination register. Remember that RO in RISC-V can only contain the value

Each stage preceed by a group of flip-flops to store the data to be passed on to the next stage in the next cycle. Each stage contain a nop bit to represent if the stage should be inactive in the following cycle.

**The simulator able to deal with two types of hazards:**
- RAW Hazards: RAW hazards are dealt with using either only forwarding (if possible) or, if not, using stalling + forwarding. Use EX-ID forwarding and MEM-ID forwarding appropriately.
- Control Flow Hazards: The branch conditions are resolved in the ID/RF stage of the pipeline.

**The simulator deals with branch instructions as follows:**
- Branches are always assumed to be NOT TAKEN. That is, when a beq is fetched in the IF stage, the PC is speculatively updated as PC+4.
- Branch conditions are resolved in the ID/RF stage.
- If the branch is determined to be not taken in the ID/RF stage (as predicted), then the pipeline proceeds without disruptions. If the branch is determined to be taken, then the speculatively fetched instruction is discarded and the nop bit is set for the ID/RR stage for the next cycle. Then the new instruction is fetched in the next cycle using the new branch PC address.

# Usage
- First, change directory with `cd` command to the one has `main.py` file.
```
cd folder_contains_main.py
```

-  Second, run the script adding the parameter `--iodir`, which is the directory contains testcase
```
python main.py --iodir folder_contains_testcases
```

## The [sample_testcases](https://github.com/jinrui-rey/RISC-V_processor_simulator/tree/main/Sample_testcases) folder contains the sample inputs and outputs, for your information


