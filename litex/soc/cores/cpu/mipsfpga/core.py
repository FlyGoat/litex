#
# This file is part of LiteX.
#
# Copyright (c) 2024 Jiaxun Yang <jiaxun.yang@flygoat.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import re

from migen import *

from litex.gen import *

from litex import get_data_mod

from litex.soc.interconnect import ahb
from litex.soc.integration.soc import SoCRegion

from litex.soc.cores.cpu import CPU

# MIPSFPGA

class MIPSFPGA(CPU):
    category             = "softcore"
    family               = "mips"
    name                 = "mipsfpga"
    human_name           = "microAptiv UP"
    variants             = ["standard"]
    data_width           = 32
    endianness           = "little"
    gcc_triple           = "mips64el-linux-gnuabi64"
    linker_output_format = "elf32-tradlittlemips"
    nop                  = "nop"
    io_regions           = {0x1000_0000: 0x0c00_0000} # Origin, Length.

    # GCC Flags.
    @property
    def gcc_flags(self):
        flags = "-march=mips32r2 -mabi=32 -msoft-float"
        flags += " -D__mipsfpga__ "
        flags += " -DUART_POLLING"
        return flags

    # Memory Mapping.
    @property
    def mem_map(self):
        # Based on vanilla sysmap.h
        return {
            "main_ram" : 0x0000_0000,
            "csr"      : 0x1800_0000,
            "sram"     : 0x1c00_0000,
            "rom"      : 0x1fc0_0000,
        }

    def __init__(self, platform, variant="standard"):
        self.platform     = platform
        self.variant      = variant
        self.reset        = Signal()
        self.interrupt    = Signal(7)
        # Peripheral bus (Connected to main SoC's bus).
        ahb_if = ahb.AHBInterface(data_width=32, address_width=32, addressing="byte")
        self.periph_buses = [ahb_if]
        # Memory buses (Connected directly to LiteDRAM).
        self.memory_buses = []

        # CPU Instance.
        self.cpu_params = dict(
            # AHB Interface
            i_HRDATA = ahb_if.rdata,
            i_HREADY = ahb_if.readyout,
            i_HRESP  = ahb_if.resp,
            i_SI_AHBStb = 1, 
            o_HRESETn = Open(),
            o_HADDR = ahb_if.addr,
            o_HBURST = ahb_if.burst,
            o_HPROT = ahb_if.prot,
            o_HMASTLOCK = ahb_if.mastlock,
            o_HSIZE = ahb_if.size,
            o_HTRANS = ahb_if.trans,
            o_HWRITE = ahb_if.write,
            o_HWDATA = ahb_if.wdata,  

            i_SI_ClkIn = ClockSignal("sys"),
            i_SI_ColdReset = ResetSignal("sys") | self.reset,
            i_SI_Endian = 0,
            i_SI_Int = self.interrupt,
            i_SI_NMI = 0,
            i_SI_Reset = ResetSignal("sys") | self.reset,
            i_SI_MergeMode = 0,

            i_SI_CPUNum = 0,
            i_SI_IPTI = 0,
            i_SI_EICPresent = 0,
            i_SI_EICVector = 0,
            i_SI_Offset = 0,
            i_SI_EISS = 0,
            i_SI_BootExcISAMode = 0,
            i_SI_SRSDisable = Constant(0xf, 4),
            i_SI_TraceDisable = 1,

            i_gscanmode = 0,
            i_gscanenable = 0,
            i_gscanin = 0,
            i_gscanramwr = 0,
            i_gmbinvoke = 0,

            i_BistIn = 0,

            i_TC_Stall = 0,
            i_TC_PibPresent = 0,
        )

        self.comb += ahb_if.sel.eq(1)

        # Add sources.
        basedir = os.path.join("mipsfpga", "rtl_up")
        self.platform.add_source_dir(basedir)
        platform.add_verilog_include_path(basedir)

    def add_jtag(self, pads):
        self.cpu_params.update(

            i_EJ_TMS  = pads.tms,
            i_EJ_TDI      = pads.tdi,
            o_EJ_TDO      = pads.tdo,
            i_EJ_TRST_N    = pads.ntrst,
            i_EJ_TCK = pads.tck,
        )


    def set_reset_address(self, reset_address):
        self.reset_address = reset_address

    def bios_map(self, addr, cached):
        if cached:
            return addr + 0x8000_0000
        else:
            return addr + 0xa000_0000

    def do_finalize(self):
        # assert hasattr(self, "reset_address")
        self.specials += Instance("m14k_top", **self.cpu_params)
