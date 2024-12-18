#
# This file is part of LiteX.
#
# Copyright (c) 2024 Jiaxun Yang <jiaxun.yang@flygoat.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import re

from migen import *
from pathlib import Path
from litex.gen import *

from litex import get_data_mod

from litex.gen import *
from litex.gen.genlib.misc import WaitTimer

from litex.soc.interconnect import axi
from litex.soc.integration.soc import SoCRegion

from litex.soc.cores.cpu import CPU

# MIPSFPGA

class i6500(CPU):
    category             = "softcore"
    family               = "mips"
    name                 = "i6500"
    human_name           = "MIPS I6500"
    variants             = ["standard"]
    data_width           = 64
    endianness           = "little"
    gcc_triple           = "mips64el-linux-gnuabi64"
    linker_output_format = "elf64-tradlittlemips"
    nop                  = "nop"
    io_regions           = {0x1000_0000: 0x0c00_0000} # Origin, Length.

    # GCC Flags.
    @property
    def gcc_flags(self):
        flags = "-march=mips64r6 -mabi=64 -msoft-float -G 0 -mno-abicalls -fno-pic"
        flags += " -D__i6500__ "
        flags += " -DUART_POLLING"
        return flags

    # Memory Mapping.
    @property
    def mem_map(self):
        # Based on vanilla sysmap.h
        return {
            "main_ram" : 0x0000_0000,
            "csr"      : 0x1000_0000,
            "sram"     : 0x1c00_0000,
            "rom"      : 0x1fc0_0000,
        }

    def __init__(self, platform, variant="standard"):
        self.platform     = platform
        self.variant      = variant
        self.reset        = Signal()
        self.interrupt    = Signal(7)
        # Peripheral bus (Connected to main SoC's bus).
        axi_if = axi.AXIInterface(data_width=64, address_width=32, id_width=11, ar_user_width=8, aw_user_width=8)
        self.periph_buses = [axi_if]
        # Memory buses (Connected directly to LiteDRAM).
        self.memory_buses = []
        self.si_cpc_reset_n = Signal()
        self.si_cluster_pwr_on_n = Signal()

        # CPU Instance.
        self.cpu_params = dict(
            i_si_ref_clk     = ClockSignal("sys"),
            i_si_reset_n     = ~ResetSignal("sys") & ~self.reset,

            i_PWR_CSS0_QREQn = 1,
            o_PWR_CSS0_QACCEPTn = Open(),
            o_PWR_CSS0_QDENY = Open(),
            o_PWR_CSS0_QACTIVE = Open(),
            o_so_cpc_clk_out = Open(),
            i_si_cpc_reset_n = self.si_cpc_reset_n,
            i_si_cluster_pwr_on_n = self.si_cluster_pwr_on_n,
            i_si_vc_run_init_load_en = 0,
            i_si_dft_reset_n = Replicate(1, 2), # CHK
            i_si_dft_pwr_up = 0,
            i_si_cm_pwr_up = 0,
            i_si_dbu_pwr_up = 0,
            i_si_cm_rail_stable = 1,
            i_si_dbu_rail_stable = 1,
            i_si_cm_vdd_ok = 1,
            i_si_dbu_vdd_ok = 1,
            i_si_cpc_l2_hw_init_inhibit = 0,

            i_si_core0_rail_stable = 1,
            i_si_core0_vdd_ok = 1,
            i_si_core0_pwr_up = 0,
            i_si_core0_cold_pwr_up = Constant(0b10, 2),
            i_si_core0_reset_hold = 0,
            i_si_core0_vc_run_init_0 = 1,
            i_si_core0_vc_run_init_1 = 0,
            i_si_core0_vc_run_init_2 = 0,
            i_si_core0_vc_run_init_3 = 0,
            o_so_core0_rail_enable = Open(),
            o_so_core0_clk = Open(),
            o_so_core0_vdd_ack = Open(),
            o_so_core0_domain_ready = Open(),
            i_si_cm_reset_hold = 0,
            i_si_dbu_cold_pwr_up = Constant(0b00, 2),
            i_si_dbu_reset_hold = 0,
            o_so_cm_clk = Open(),
            o_so_cm_reset_n = Open(),
            o_so_cm_cold_reset = Open(),
            o_so_cm_rail_enable = Open(),
            o_so_dbu_rail_enable = Open(),
            o_so_cm_vdd_ack = Open(),
            o_so_dbu_vdd_ack = Open(),
            o_so_cm_domain_ready = Open(),
            o_so_dbu_domain_ready = Open(),

            i_si_io_core0_clk_ratio = Constant(0, 3),
            i_si_io_core0_supports_semisync = 0,
            i_si_io_core0_clk_ratio_change_en = 0,
            i_si_io_mem_clk_ratio = Constant(0, 3),
            i_si_io_mem_supports_semisync = 0,
            i_si_io_mem_clk_ratio_change_en = 0,

            i_si_io_cm_clk_ratio = Constant(0, 3),
            i_si_io_cm_clk_ratio_change_en = 0,

            i_si_io_clk_prescale = Constant(0, 3),
            i_si_io_clk_prescale_change_en = 0,

            i_si_io_set_clk_ratio = 0,
            o_so_io_clk_change_active = Open(),

            # ej_trst_n
            # ej_tck
            # ej_tms
            # ej_tdi
            # ej_tdo
            # ej_tdo_zstate

            o_so_ej_dbg_out = Open(8),
            i_si_ej_disable_probe_debug = 0,
            o_si_ej_disable_other_debug = 0,

            i_si_ej_manuf_id = Constant(0, 11),
            i_si_ej_part_num = Constant(0, 16),
            i_si_ej_version = Constant(0, 4),

            i_si_dbu_tp_mode = Constant(0, 2),
            i_si_dbu_tp_pclk = 0,
            i_si_dbu_tp_paddr = Constant(0, 10),
            i_si_dbu_tp_psel = 0,
            i_si_dbu_tp_penable = 0,
            i_si_dbu_tp_pwrite = 0,
            i_si_dbu_tp_pwdata = Constant(0, 32),
            o_so_dbu_tp_prdata = Open(32),
            o_so_dbu_tp_pready = Open(),
            o_so_dbu_tp_pslverr = Open(),

            i_si_big_endian = 0,

            o_so_cm_err = Open(),
            o_so_cm_perf_cnt_int = Open(),
            i_si_ugcr_present = 0,
            i_si_new_bev_base_load_en = 0,
            i_si_new_bev_base = Constant(0, 36), # Check
            i_si_new_bev_base_mode = 0,

            i_si_cm_int = self.interrupt,
            i_si_external_ej_debug_m = 0,
            o_so_external_ej_dint_out = Open(),

            o_so_cm_mem_sleep = Open(),

            i_si_bist_to_cm = 0,
            o_so_bist_from_cm = Open(),

            i_si_bist_to_core0 = 0,
            o_so_bist_from_core0 = Open(),

            o_MEM_ACLK_OUT = Open(),
            i_MEM_ACLK_IN = ClockSignal("sys"),
            o_MEM_ARESETn = Open(),
            o_MEM_ARVALID = axi_if.ar.valid,
            i_MEM_ARREADY = axi_if.ar.ready,
            o_MEM_ARID = axi_if.ar.id,
            o_MEM_ARADDR = axi_if.ar.addr,
            o_MEM_ARLEN = axi_if.ar.len,
            o_MEM_ARSIZE = axi_if.ar.size,
            o_MEM_ARBURST = axi_if.ar.burst,
            o_MEM_ARLOCK = axi_if.ar.lock,
            o_MEM_ARCACHE = axi_if.ar.cache,
            o_MEM_ARPROT = axi_if.ar.prot,
            o_MEM_ARQOS = axi_if.ar.qos,
            o_MEM_ARUSER = axi_if.ar.user,
            o_MEM_AWVALID = axi_if.aw.valid,
            i_MEM_AWREADY = axi_if.aw.ready,
            o_MEM_AWID = axi_if.aw.id,
            o_MEM_AWADDR = axi_if.aw.addr,
            o_MEM_AWLEN = axi_if.aw.len,
            o_MEM_AWSIZE = axi_if.aw.size,
            o_MEM_AWBURST = axi_if.aw.burst,
            o_MEM_AWLOCK = axi_if.aw.lock,
            o_MEM_AWCACHE = axi_if.aw.cache,
            o_MEM_AWPROT = axi_if.aw.prot,
            o_MEM_AWQOS = axi_if.aw.qos,
            o_MEM_AWUSER = axi_if.aw.user,
            o_MEM_WVALID = axi_if.w.valid,
            i_MEM_WREADY = axi_if.w.ready,
            o_MEM_WDATA = axi_if.w.data,
            o_MEM_WSTRB = axi_if.w.strb,
            o_MEM_WLAST = axi_if.w.last,
            i_MEM_RVALID = axi_if.r.valid,
            o_MEM_RREADY = axi_if.r.ready,
            i_MEM_RID = axi_if.r.id,
            i_MEM_RDATA = axi_if.r.data,
            i_MEM_RRESP = axi_if.r.resp,
            i_MEM_RLAST = axi_if.r.last,
            i_MEM_BVALID = axi_if.b.valid,
            o_MEM_BREADY = axi_if.b.ready,
            i_MEM_BID = axi_if.b.id,
            i_MEM_BRESP = axi_if.b.resp,

            o_so_fault = Open(12),
            i_si_parity_enable = 0, # CHK

            i_tst_scan_mode = 0,
            i_tst_scan_en = 0,

            i_si_core0_tst_scan_si = Constant(0, 8),
            o_so_core0_tst_scan_so = Open(8),
            i_si_cm_tst_scan_si = Constant(0, 16),
            o_so_cm_tst_scan_so = Open(16),
            i_si_clkgen_tst_scan_si = 0,
            o_so_clkgen_tst_scan_so = Open(),
        )

        trst_timer = WaitTimer(128)
        self.submodules += trst_timer

        self.fsm = fsm = ResetInserter()(FSM(reset_state="RST"))
        fsm.act("RST",
            trst_timer.wait.eq(1),
            self.si_cpc_reset_n.eq(0),
            self.si_cluster_pwr_on_n.eq(0),
            If(trst_timer.done,
                NextState("PWR_UP")
            )
        )

        fsm.act("PWR_UP",
                self.si_cpc_reset_n.eq(1),
                self.si_cluster_pwr_on_n.eq(1)
                )

        # Add sources.
        basedir = os.environ["MIPS_HOME"]
        filelist_path = os.path.join(Path(basedir).parent.absolute(), "filelists", "i65litex_soc_syn.f")
        filelist = open(filelist_path, 'r')
        lines = filelist.readlines()
        is_file = False
        for line in lines:
            if "set INC_DIRS" in line:
                is_file = False
                continue
            
            if "set RTL_SOURCE_FILES" in line:
                is_file = True
                continue

            line = line.rstrip().rstrip('\\').rstrip()

            res = re.search(r"\$MIPS_HOME\/(.+)", line)
            if not res is None:
                if not is_file:
                    platform.add_verilog_include_path(os.path.join(basedir, res.group(1)))
                else:
                    platform.add_source(os.path.join(basedir, res.group(1)))

    def add_jtag(self, pads):
        self.cpu_params.update(

            i_ej_tms  = pads.tms,
            i_ej_tdi      = pads.tdi,
            o_ej_tdo      = pads.tdo,
            i_ej_trst_n    = pads.ntrst,
            i_ej_tck = pads.tck,
        )


    def set_reset_address(self, reset_address):
        self.reset_address = reset_address

    def bios_map(self, addr, cached):
        if cached:
            return addr + 0xffff_ffff_8000_0000
        else:
            return addr + 0xffff_ffff_a000_0000

    def do_finalize(self):
        # assert hasattr(self, "reset_address")
        self.specials += Instance("mips_soc", **self.cpu_params)
