import os
import argparse

MemSize = 1000  # memory size, in reality, the memory size should be 2^32, but for this lab, for the space resaon, we keep it as this large number, but the memory is still 32-bit addressable.


class Conv_Bin:
    # Convert a number to a binary string with a specified number of bits
    def convertBinary(self, n, bits):
        s = bin(n & int("1" * bits, 2))[2:]
        return ("{0:0>%s}" % (bits)).format(s)

    # Convert binary to two's complement representation
    def twosCompBinary(self, bin, digit):
        while len(bin) < digit:
            bin = '0' + bin

        if bin[0] == '0':
            return int(bin, 2)
        else:
            return -1 * (int(''.join('1' if x == '0' else '0' for x in bin), 2) + 1)


class InsMem:
    # Constructor and method to read instruction memory
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(self.ioDir + "/imem.txt") as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]

    def readInstr(self, ReadAddress):
        # read instruction memory
        # return 32 bit hex val
        address = ReadAddress - ReadAddress % 4
        return "".join(self.IMem[address:address + 4])


class DataMem:
    # Constructor and methods to read and write data memory
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(ioDir + "/dmem.txt") as dm:
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]

        self.DMem.extend(['00000000' for i in range(MemSize - len(self.DMem))])

    def readDataMem(self, ReadAddress):
        # read data memory
        # return 32 bit hex val
        address = ReadAddress - ReadAddress % 4
        return int("".join(self.DMem[address:address + 4]), 2)

    def writeDataMem(self, address, WriteData):
        # write data into byte addressable memory
        WriteData = Conv_Bin().convertBinary(WriteData, 32)
        newAddress = address - address % 4
        for i in range(4):
            self.DMem[newAddress + i] = WriteData[8 * i:8 * i + 8]
        pass

    def outputDataMem(self):
        #resPath = os.path.join(self.opDir)
        resPath = os.path.join(self.ioDir, self.id + "_DMEMResult.txt")

        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])


class RegisterFile:
    # Constructor and methods to read and write register file
    def __init__(self, ioDir, id):
        # self.outputFile = opDir + id +"RFResult.txt"
        self.outputFile = os.path.join(ioDir, id + "RFResult.txt")
        self.Registers = ["".join(["0" for x in range(32)]) for i in range(32)]

    def readRF(self, Reg_addr):
        return int(self.Registers[Reg_addr], 2)

    def writeRF(self, Reg_addr, Wrt_reg_data):
        if Reg_addr == 0:
            return
        self.Registers[Reg_addr] = Conv_Bin().convertBinary(Wrt_reg_data, 32)
        pass

    def outputRF(self, cycle):
        op = ["-" * 70 + "\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        op.extend([str(val) + "\n" for val in self.Registers])
        if (cycle == 0):
            perm = "w"
        else:
            perm = "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)


class State:
    # Constructor for initializing pipeline stages
    def __init__(self):
        self.IF = {"nop": True, "PC": 0}
        self.ID = {"nop": True, "Instr": 0}
        self.EX = {"nop": True, "Read_data1": 0, "Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0,
                   "is_I_type": False, "rd_mem": 0,
                   "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = {"nop": True, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0,
                    "wrt_mem": 0, "wrt_enable": 0}
        self.WB = {"nop": True, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "wrt_enable": 0}


class registerPipeline:

    def __init__(self):
        self.IF2ID = {"PC": 0, "rawInstruction": 0}
        self.ID2EX = {"PC": 0, "instruction": 0, "rs": 0, "rt": 0}
        self.EX2MEM = {"PC": 0, "instruction": 0, "ALUresult": 0, "rt": 0}
        self.MEM2WB = {"PC": 0, "instruction": 0, "Wrt_data": 0, "ALUresult": 0, "rt": 0}


# Define a class for hazard checking
class checkHazards():
    # Methods to check different types of hazards
    def hazardRegWrite(self, pr: registerPipeline, rs):
        return rs != 0 and pr.MEM2WB["instruction"] and pr.MEM2WB["instruction"]["registerWrite"] and \
            pr.MEM2WB["instruction"]["Wrt_reg_addr"] == rs

    def hazardLoad(self, pr: registerPipeline, rs1, rs2):
        return pr.ID2EX["instruction"] and pr.ID2EX["instruction"]["rd_mem"] and \
            (pr.ID2EX["instruction"]["Wrt_reg_addr"] == int(rs1, 2) or pr.ID2EX["instruction"]["Wrt_reg_addr"] == int(
                rs2, 2))

    def hazardMEM(self, pr: registerPipeline, rs):
        return pr.MEM2WB["instruction"] and pr.MEM2WB["instruction"]["registerWrite"] and \
            pr.MEM2WB["instruction"]["Wrt_reg_addr"] != 0 and \
            pr.MEM2WB["instruction"]["Wrt_reg_addr"] == rs

    def hazardEX(self, pr: registerPipeline, rs):
        return pr.EX2MEM["instruction"] and pr.EX2MEM["instruction"]["registerWrite"] and not pr.EX2MEM["instruction"][
            "rd_mem"] and \
            pr.EX2MEM["instruction"]["Wrt_reg_addr"] != 0 and \
            pr.EX2MEM["instruction"]["Wrt_reg_addr"] == rs


class Core():
    # Constructor and core functionalities
    def __init__(self, ioDir, imem, dmem, id):
        self.myRF = RegisterFile(ioDir, id)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        #self.opDir = opDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem
        self.state.IF["nop"] = False
        self.regPipeline = registerPipeline()
        self.checkHazards = checkHazards()


class SingleStageCore(Core):
    # Constructor and methods for single-stage core operations
    def __init__(self, ioDir, imem, dmem, id):
        super(SingleStageCore, self).__init__(ioDir, imem, dmem, id)
        self.opFilePath = ioDir + "/StateResult_SS.txt"

    def WriteBack(self):
        if not self.state.WB["nop"]:

            if self.state.WB["registerWrite"]:
                Reg_addr = self.state.WB["Wrt_reg_addr"]

                if self.state.EX["memReg"]:
                    Wrt_reg_data = self.state.MEM["Wrt_data"]

                else:
                    Wrt_reg_data = self.state.MEM["ALUresult"]

                self.myRF.writeRF(Reg_addr, Wrt_reg_data)

    def LoadStore(self):
        self.state.WB["nop"] = self.state.MEM["nop"]

        if not self.state.MEM["nop"]:
            if self.state.MEM["wrt_mem"]:
                writeData = self.state.EX["Read_data2"]
                writeAddress = self.state.MEM["ALUresult"]
                self.ext_dmem.writeDataMem(writeAddress, writeData)

            if self.state.MEM["rd_mem"]:
                readAddress = self.state.MEM["ALUresult"]
                self.state.MEM["Wrt_data"] = self.ext_dmem.readDataMem(readAddress)
            self.state.MEM["Wrt_reg_addr"] = self.state.EX["Wrt_reg_addr"]

            self.state.WB["registerWrite"] = self.state.EX["registerWrite"]
            self.state.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]

        else:
            self.state.WB["nop"] = True

    def InstructionExecute(self):
        self.state.MEM["nop"] = self.state.EX["nop"]
        if not self.state.EX["nop"]:

            if self.state.EX["imm"] != "X":
                op2 = self.state.EX["imm"]

            else:
                op2 = self.state.EX["Read_data2"]

            # addition
            if self.state.EX["aluControl"] == "0010":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] + op2

            # subtraction
            if self.state.EX["aluControl"] == "0110":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] - op2

            # and operation
            if self.state.EX["aluControl"] == "0000":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] & op2

            # or operation
            if self.state.EX["aluControl"] == "0001":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] | op2

            # xor operation
            if self.state.EX["aluControl"] == "0011":
                self.state.MEM["ALUresult"] = self.state.EX["Read_data1"] ^ op2

            # branch
            if self.state.EX["branch"]:
                if self.state.EX["func3"] == "000" and self.state.MEM["ALUresult"] == 0:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True

                elif self.state.EX["func3"] == "001" and self.state.MEM["ALUresult"] != 0:
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])
                    self.nextState.IF["nop"] = False
                    self.state.MEM["nop"] = True

                elif self.state.EX["func3"] == "X":
                    self.nextState.IF["nop"] = False
                    self.nextState.IF["PC"] = self.state.IF["PC"] + (self.state.EX["pcJump"])

            self.state.MEM["rd_mem"] = self.state.EX["rd_mem"]
            self.state.MEM["wrt_mem"] = self.state.EX["wrt_mem"]

    def InstructionDecode(self):
        self.state.EX["nop"] = self.state.ID["nop"]

        if not self.state.ID["nop"]:
            instructionReverse = self.state.ID["Instr"][::-1]
            opcode = instructionReverse[0:7]

            # R-type instruction
            if opcode == "1100110":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                rd = instructionReverse[7:12][::-1]
                func7 = instructionReverse[25:32][::-1]
                func3 = instructionReverse[12:15][::-1] + func7[1]

                aluContol = {"0000": "0010", "0001": "0110", "1110": "0000", "1100": "0001", "1000": "0011"}
                self.state.EX = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                 "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                 "imm": "X", "Rs": 0, "Rt": 0, "pcJump": 0,
                                 "is_I_type": False, "rd_mem": 0, "aluSource": 0, "aluControl": aluContol[func3],
                                 "alu_op": "10",
                                 "Wrt_reg_addr": int(rd, 2), "wrt_mem": 0, "registerWrite": 1, "branch": 0, "memReg": 0}

            # I-type instruction
            if opcode == "1100100":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]
                func3 = instructionReverse[12:15][::-1]

                aluContol = {"000": "0010", "111": "0000", "110": "0001", "100": "0011"}
                self.state.EX = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)), "Read_data2": 0,
                                 "imm": Conv_Bin().twosCompBinary(imm, 12), "Rs": 0, "Rt": 0, "pcJump": 0,
                                 "is_I_type": True, "rd_mem": 0, "aluSource": 1, "aluControl": aluContol[func3],
                                 "alu_op": "00",
                                 "Wrt_reg_addr": int(rd, 2), "wrt_mem": 0, "registerWrite": 1, "branch": 0, "memReg": 0}

            # I-type instruction
            if opcode == "1100000":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]

                self.state.EX = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)), "Read_data2": 0,
                                 "imm": Conv_Bin().twosCompBinary(imm, 12), "Rs": 0, "Rt": 0, "pcJump": 0,
                                 "is_I_type": False, "rd_mem": 1, "aluSource": 1, "aluControl": "0010", "alu_op": "00",
                                 "Wrt_reg_addr": int(rd, 2), "wrt_mem": 0, "registerWrite": 1, "branch": 0, "memReg": 1}

            # S-type instruction
            if opcode == "1100010":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = instructionReverse[7:12] + instructionReverse[25:32]
                imm = imm[::-1]

                self.state.EX = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                 "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                 "imm": int(imm, 2), "Rs": 0, "Rt": 0, "pcJump": 0,
                                 "is_I_type": False, "rd_mem": 0, "aluSource": 1, "aluControl": "0010", "alu_op": "00",
                                 "Wrt_reg_addr": "X", "wrt_mem": 1, "registerWrite": 0, "branch": 0, "memReg": "X"}

                # SB-type instruction
            if opcode == "1100011":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = "0" + instructionReverse[8:12] + instructionReverse[25:31] + instructionReverse[7] + \
                      instructionReverse[31]  # check
                imm = imm[::-1]
                func3 = instructionReverse[12:15][::-1]

                self.state.EX = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                 "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                 "imm": "X", "Rs": 0, "Rt": 0, "pcJump": Conv_Bin().twosCompBinary(imm, 13),
                                 "is_I_type": False, "rd_mem": 0, "aluSource": 0, "aluControl": "0110", "alu_op": "01",
                                 "Wrt_reg_addr": "X", "wrt_mem": 0, "registerWrite": 0, "branch": 1, "memReg": "X",
                                 "func3": func3}
            # UJ-type instruction
            if opcode == "1111011":
                rs1 = instructionReverse[15:20][::-1]
                rd = instructionReverse[7:12][::-1]
                imm = "0" + instructionReverse[21:31] + instructionReverse[20] + instructionReverse[12:20] + \
                      instructionReverse[31]  # check
                imm = imm[::-1]

                self.state.EX = {"nop": False, "Read_data1": self.state.IF['PC'], "Read_data2": 4,
                                 "imm": "X", "Rs": 0, "Rt": 0, "pcJump": Conv_Bin().twosCompBinary(imm, 21),
                                 "is_I_type": False, "rd_mem": 0, "aluSource": 1, "aluControl": "0010", "alu_op": "10",
                                 "Wrt_reg_addr": int(rd, 2), "wrt_mem": 0, "registerWrite": 1, "branch": 1, "memReg": 0,
                                 "func3": "X"}

    def InstructionFetch(self):

        self.state.ID["Instr"] = self.ext_imem.readInstr(self.state.IF["PC"])
        instructionReverse = self.state.ID["Instr"][::-1]
        opcode = instructionReverse[0:7]

        if opcode == "1111111":
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.IF["nop"] = True

        else:
            self.nextState.IF["nop"] = False
            self.nextState.IF["PC"] = self.state.IF["PC"] + 4
            self.state.ID["nop"] = False

    def step(self):

        # Your implementation
        self.InstructionFetch()
        self.InstructionDecode()
        self.InstructionExecute()
        self.LoadStore()
        self.WriteBack()

        if self.state.IF["nop"]:
            self.halted = True

        self.myRF.outputRF(self.cycle)
        self.printState(self.nextState, self.cycle)

        self.state = self.nextState
        self.nextState = State()
        self.cycle += 1

        return self.cycle

    def printState(self, state, cycle):
        printstate = ["-" * 70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")

        if (cycle == 0):
            perm = "w"
        else:
            perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


class FiveStageCore(Core):

    def __init__(self, ioDir, imem, dmem, id):
        super(FiveStageCore, self).__init__(ioDir, imem, dmem, id)
        self.opFilePath = ioDir + "/StateResult_FS.txt"

    def WriteBack(self):

        if not self.state.WB["nop"]:
            instruction = self.regPipeline.MEM2WB["instruction"]

            if instruction["registerWrite"]:
                Reg_addr = instruction["Wrt_reg_addr"]
                Wrt_reg_data = self.regPipeline.MEM2WB["Wrt_data"]
                self.myRF.writeRF(Reg_addr, Wrt_reg_data)

    def LoadStore(self):

        self.nextState.WB["nop"] = self.state.MEM["nop"]

        if not self.state.MEM["nop"]:
            pc = self.regPipeline.EX2MEM["PC"]
            instruction = self.regPipeline.EX2MEM["instruction"]
            alu_result = self.regPipeline.EX2MEM["ALUresult"]
            rs2 = self.regPipeline.EX2MEM["Rs2"]

            if instruction["wrt_mem"]:
                writeData = self.myRF.readRF(rs2)
                writeAddress = alu_result
                self.ext_dmem.writeDataMem(writeAddress, writeData)

            if instruction["rd_mem"]:
                readAddress = alu_result
                wrt_mem_data = self.ext_dmem.readDataMem(readAddress)

            if instruction["memReg"] == 1:
                self.regPipeline.MEM2WB["Wrt_data"] = wrt_mem_data

            else:
                self.regPipeline.MEM2WB["Wrt_data"] = alu_result

            self.regPipeline.MEM2WB["PC"] = pc
            self.regPipeline.MEM2WB["instruction"] = instruction

    def InstructionExecute(self):

        self.nextState.MEM["nop"] = self.state.EX["nop"]

        if not self.state.EX["nop"]:
            pc = self.regPipeline.ID2EX["PC"]
            instruction = self.regPipeline.ID2EX["instruction"]
            rs2 = self.regPipeline.ID2EX["Rs2"]
            self.state.EX = self.regPipeline.ID2EX["instruction"]

            if self.state.EX["imm"] != "X":
                op2 = self.state.EX["imm"]

            else:
                op2 = self.state.EX["Read_data2"]

            # addition
            if self.state.EX["aluControl"] == "0010":
                alu_result = self.state.EX["Read_data1"] + op2

            # subtraction
            if self.state.EX["aluControl"] == "0110":
                alu_result = self.state.EX["Read_data1"] - op2

            # and
            if self.state.EX["aluControl"] == "0000":
                alu_result = self.state.EX["Read_data1"] & op2

            # or
            if self.state.EX["aluControl"] == "0001":
                alu_result = self.state.EX["Read_data1"] | op2

            # xor
            if self.state.EX["aluControl"] == "0011":
                alu_result = self.state.EX["Read_data1"] ^ op2

            self.regPipeline.EX2MEM["PC"] = pc
            self.regPipeline.EX2MEM["instruction"] = instruction
            self.regPipeline.EX2MEM["ALUresult"] = alu_result
            self.regPipeline.EX2MEM["Rs2"] = rs2

    def InstructionDecode(self):
        self.nextState.EX["nop"] = self.state.ID["nop"]

        if not self.state.ID["nop"]:
            instructionReverse = self.regPipeline.IF2ID["rawInstruction"][::-1]
            self.regPipeline.ID2EX["PC"] = self.regPipeline.IF2ID["PC"]
            pc = self.regPipeline.IF2ID["PC"]
            opcode = instructionReverse[0:7]

            # R-type instruction
            if opcode == "1100110":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                rd = instructionReverse[7:12][::-1]
                func7 = instructionReverse[25:32][::-1]
                func3 = instructionReverse[12:15][::-1] + func7[1]

                aluContol = {"0000": "0010", "0001": "0110", "1110": "0000", "1100": "0001", "1000": "0011"}
                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                                         "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                                         "imm": "X", "pcJump": 0, "Rs": int(rs1, 2), "Rt": int(rs2, 2),
                                                         "Wrt_reg_addr": int(rd, 2), "is_I_type": False, "rd_mem": 0,
                                                         "aluSource": 0, "aluControl": aluContol[func3],
                                                         "wrt_mem": 0, "alu_op": "10", "registerWrite": 1, "branch": 0,
                                                         "memReg": 0}

            # I-type instruction
            if opcode == "1100100":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]
                func3 = instructionReverse[12:15][::-1]

                aluContol = {"000": "0010", "111": "0000", "110": "0001", "100": "0011"}
                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                                         "Read_data2": 0,
                                                         "imm": Conv_Bin().twosCompBinary(imm, 12), "pcJump": 0,
                                                         "Rs": int(rs1, 2),
                                                         "Rt": 0,
                                                         "Wrt_reg_addr": int(rd, 2), "is_I_type": True, "rd_mem": 0,
                                                         "aluSource": 1, "aluControl": aluContol[func3],
                                                         "wrt_mem": 0, "alu_op": "00", "registerWrite": 1, "branch": 0,
                                                         "memReg": 0}

            # I-type instruction
            if opcode == "1100000":
                rs1 = instructionReverse[15:20][::-1]
                imm = instructionReverse[20:32][::-1]
                rd = instructionReverse[7:12][::-1]
                func3 = instructionReverse[12:15][::-1]

                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                                         "Read_data2": 0,
                                                         "imm": Conv_Bin().twosCompBinary(imm, 12), "pcJump": 0,
                                                         "Rs": int(rs1, 2),
                                                         "Rt": 0,
                                                         "Wrt_reg_addr": int(rd, 2), "is_I_type": False, "rd_mem": 1,
                                                         "aluSource": 1, "aluControl": "0010",
                                                         "wrt_mem": 0, "alu_op": "00", "registerWrite": 1, "branch": 0,
                                                         "memReg": 1}

            # S-type instruction
            if opcode == "1100010":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = instructionReverse[7:12] + instructionReverse[25:32]
                imm = imm[::-1]

                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                                         "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                                         "imm": int(imm, 2), "Rs": int(rs1, 2), "Rt": int(rs2, 2),
                                                         "pcJump": 0,
                                                         "is_I_type": False, "rd_mem": 0, "aluSource": 1,
                                                         "aluControl": "0010", "alu_op": "00",
                                                         "Wrt_reg_addr": "X", "wrt_mem": 1, "registerWrite": 0,
                                                         "branch": 0, "memReg": "X"}

            # SB-type instruction
            if opcode == "1100011":
                rs1 = instructionReverse[15:20][::-1]
                rs2 = instructionReverse[20:25][::-1]
                imm = "0" + instructionReverse[8:12] + instructionReverse[25:31] + instructionReverse[7] + \
                      instructionReverse[31]
                imm = imm[::-1]
                func3 = instructionReverse[12:15][::-1]

                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": self.myRF.readRF(int(rs1, 2)),
                                                         "Read_data2": self.myRF.readRF(int(rs2, 2)),
                                                         "imm": "X", "Rs": int(rs1, 2), "Rt": int(rs2, 2),
                                                         "pcJump": Conv_Bin().twosCompBinary(imm, 13),
                                                         "is_I_type": False, "rd_mem": 0, "aluSource": 0,
                                                         "aluControl": "0110", "alu_op": "01",
                                                         "Wrt_reg_addr": "X", "wrt_mem": 0, "registerWrite": 0,
                                                         "branch": 1, "memReg": "X", "func3": func3}

            # UJ-type instruction
            if opcode == "1111011":
                rs1 = instructionReverse[15:20][::-1]
                imm = "0" + instructionReverse[21:31] + instructionReverse[20] + instructionReverse[12:20] + \
                      instructionReverse[31]
                imm = imm[::-1]
                rd = instructionReverse[7:12][::-1]

                self.regPipeline.ID2EX["instruction"] = {"nop": False, "Read_data1": pc, "Read_data2": 4,
                                                         "imm": "X", "Rs": 0, "Rt": 0,
                                                         "pcJump": Conv_Bin().twosCompBinary(imm, 21),
                                                         "is_I_type": False, "rd_mem": 0, "aluSource": 1,
                                                         "aluControl": "0010", "alu_op": "10",
                                                         "Wrt_reg_addr": int(rd, 2), "wrt_mem": 0, "registerWrite": 1,
                                                         "branch": 1, "memReg": 0, "func3": "X"}

            if self.checkHazards.hazardRegWrite(
                    self.regPipeline, self.regPipeline.ID2EX["instruction"]["Rs"]
            ):
                self.regPipeline.ID2EX["instruction"]["Read_data1"] = self.regPipeline.MEM2WB["Wrt_data"]

            if self.checkHazards.hazardRegWrite(
                    self.regPipeline, self.regPipeline.ID2EX["instruction"]["Rt"]
            ):
                self.regPipeline.ID2EX["instruction"]["Read_data2"] = self.regPipeline.MEM2WB["Wrt_data"]

            self.regPipeline.ID2EX["Rs1"] = self.regPipeline.ID2EX["instruction"]["Rs"]
            self.regPipeline.ID2EX["Rs2"] = self.regPipeline.ID2EX["instruction"]["Rt"]

            if self.checkHazards.hazardEX(
                    self.regPipeline, self.regPipeline.ID2EX["Rs1"]
            ):
                self.regPipeline.ID2EX["instruction"]["Read_data1"] = self.regPipeline.EX2MEM["ALUresult"]

            elif self.checkHazards.hazardMEM(
                    self.regPipeline, self.regPipeline.ID2EX["Rs1"]
            ):
                self.regPipeline.ID2EX["instruction"]["Read_data1"] = self.regPipeline.MEM2WB["Wrt_data"]

            if self.regPipeline.ID2EX["instruction"]["imm"] == "X":
                if self.checkHazards.hazardEX(self.regPipeline, self.regPipeline.ID2EX["Rs2"]):
                    self.regPipeline.ID2EX["instruction"]["Read_data2"] = self.regPipeline.EX2MEM["ALUresult"]

                elif self.checkHazards.hazardMEM(self.regPipeline, self.regPipeline.ID2EX["Rs2"]):
                    self.regPipeline.ID2EX["instruction"]["Read_data2"] = self.regPipeline.MEM2WB["Wrt_data"]

            if self.regPipeline.ID2EX["instruction"]["branch"]:
                if self.regPipeline.ID2EX["instruction"]["func3"] == "000" and self.regPipeline.ID2EX["instruction"][
                    "Read_data1"] - self.regPipeline.ID2EX["instruction"]["Read_data2"] == 0:
                    self.nextState.IF["nop"] = False
                    self.nextState.IF["PC"] = pc + (self.regPipeline.ID2EX["instruction"]["pcJump"])
                    self.state.IF["nop"] = self.nextState.EX["nop"] = self.nextState.ID["nop"] = True

                elif self.regPipeline.ID2EX["instruction"]["func3"] == "001" and self.regPipeline.ID2EX["instruction"][
                    "Read_data1"] - self.regPipeline.ID2EX["instruction"]["Read_data2"] != 0:
                    self.nextState.IF["nop"] = False
                    self.nextState.IF["PC"] = pc + (self.regPipeline.ID2EX["instruction"]["pcJump"])
                    self.state.IF["nop"] = self.nextState.EX["nop"] = self.nextState.ID["nop"] = True

                elif self.regPipeline.ID2EX["instruction"]["func3"] == "X":
                    self.nextState.IF["nop"] = False
                    self.nextState.IF["PC"] = pc + (self.regPipeline.ID2EX["instruction"]["pcJump"])
                    self.state.IF["nop"] = self.nextState.ID["nop"] = True

                else:
                    self.nextState.EX["nop"] = True

        else:
            self.regPipeline.ID2EX = {"PC": 0, "instruction": 0, "rs": 0, "rt": 0}

    def InstructionFetch(self):
        self.nextState.ID["nop"] = self.state.IF["nop"]

        if not self.state.IF["nop"]:
            self.regPipeline.IF2ID["rawInstruction"] = self.ext_imem.readInstr(self.state.IF["PC"])
            self.regPipeline.IF2ID["PC"] = self.state.IF["PC"]
            instructionReverse = self.regPipeline.IF2ID["rawInstruction"][::-1]

            opcode = instructionReverse[0:7]
            if opcode == "1111111":
                self.nextState.ID["nop"] = self.state.IF["nop"] = True

            else:
                self.nextState.IF["nop"] = False
                self.nextState.IF["PC"] = self.state.IF["PC"] + 4

                if self.checkHazards.hazardLoad(self.regPipeline, instructionReverse[15:20][::-1],
                                                instructionReverse[20:25][::-1]):
                    self.nextState.ID["nop"] = True
                    self.nextState.IF["PC"] = self.state.IF["PC"]

    def step(self):
        # Your implementation
        # --------------------- WB stage ---------------------
        self.WriteBack()

        # --------------------- MEM stage --------------------
        self.LoadStore()

        # --------------------- EX stage ---------------------
        self.InstructionExecute()

        # --------------------- ID stage ---------------------
        self.InstructionDecode()

        # --------------------- IF stage ---------------------
        self.InstructionFetch()

        if self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and \
                self.state.WB["nop"]:
            self.halted = True

        self.myRF.outputRF(self.cycle)
        self.PrintState(self.regPipeline, self.cycle)
        self.state = self.nextState
        self.nextState = State()
        self.cycle += 1

        return self.cycle

    def PrintState(self, state, cycle):
        printstate = ["-" * 70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.extend(["IF2ID" + key + ": " + str(val) + "\n" for key, val in state.IF2ID.items()])
        printstate.extend(["ID2EX" + key + ": " + str(val) + "\n" for key, val in state.ID2EX.items()])
        printstate.extend(["EX2MEM" + key + ": " + str(val) + "\n" for key, val in state.EX2MEM.items()])
        printstate.extend(["MEM2WB" + key + ": " + str(val) + "\n" for key, val in state.MEM2WB.items()])

        if (cycle == 0):
            perm = "w"
        else:
            perm = "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)


class MetricsGenerator(Core):

    # Constructor and method for generating performance metrics
    def __init__(self, ioDir, ss_cycle, fs_cycle):
        self.newFile = open(ioDir + "/PerformanceMetrics_Result.txt", "w")

        self.newFile.write("Single Stage Core Performance Metrics-----------------------------\n")
        self.newFile.write("Number of cycles: " + str(ss_cycle) + "\n")

        with open(ioDir + "/imem.txt", "r") as fp:
            x = len(fp.readlines()) / 4

        ss_CPI = ss_cycle / x
        ss_CPI = round(ss_CPI, 5)
        self.newFile.write("Cycles per instruction: " + str(ss_CPI) + "\n")

        ss_IPC = 1 / ss_CPI
        ss_IPC = round(ss_IPC, 6)
        self.newFile.write("Instructions per cycle: " + str(ss_IPC) + "\n")

        self.newFile.write("\nFive Stage Core Performance Metrics-----------------------------\n")
        self.newFile.write("Number of cycles: " + str(fs_cycle) + "\n")

        fs_CPI = fs_cycle / x
        fs_CPI = round(fs_CPI, 5)
        self.newFile.write("Cycles per instruction: " + str(fs_CPI) + "\n")

        fs_IPC = 1 / fs_CPI
        fs_IPC = round(fs_IPC, 6)
        self.newFile.write("Instructions per cycle: " + str(fs_IPC) + "\n")


# Main function to run the simulation
if __name__ == "__main__":
    # Setup and run the simulation for both single-stage and five-stage cores
    parser = argparse.ArgumentParser(description='RV32I processor')
    parser.add_argument('--iodir', default="./input/testcase1", type=str, help='Directory containing the input files.')
    args = parser.parse_args()

    ioDir = args.iodir
    print("IO Directory:", ioDir)

    imem = InsMem("imem", ioDir)
    dmem_ss = DataMem("SS", ioDir)
    dmem_fs = DataMem("FS", ioDir)
    ssCore = SingleStageCore(ioDir, imem, dmem_ss, 'SS_')
    fsCore = FiveStageCore(ioDir, imem, dmem_fs, 'FS_')

    while 1:
        if not ssCore.halted:
            ss_cycle = ssCore.step()

        if not fsCore.halted:
            fs_cycle = fsCore.step()

        if ssCore.halted and fsCore.halted:
            break
    MetricsGenerator(ioDir, ss_cycle, fs_cycle)

    dmem_ss.outputDataMem()
    dmem_fs.outputDataMem()
