.global main
.global isr
.global _start

_start:
  j crt_init
  nop
  nop
  nop
  nop
  nop
  nop
  nop

crt_init:
  dla $sp, _fstack

data_init:
	dla	$t0, _fdata
	dla	$t1, _edata
	dla	$t2, _fdata_rom
data_loop:
	beq	$t0, $t1, data_done
	ld	$t3, 0($t2)
  	sd	$t3, 0($t0)
	daddiu	$t0, $t0, 8
  	daddiu	$t2, $t2, 8
  	b	data_loop
data_done:

bss_init:
	dla	$t0, _fbss
  	dla	$t1, _ebss
bss_loop:
	beq	$t0, $t1, bss_done
  	sd	$zero, 0($t0)
  	daddiu	$t0, $t0, 8
	b	bss_loop
bss_done:

  dla  $t9, main
  jalr $t9
inf_loop:
  b inf_loop
