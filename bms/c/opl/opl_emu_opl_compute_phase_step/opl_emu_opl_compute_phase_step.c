#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
;
static uint32_t opl_emu_opl_compute_phase_step(uint32_t block_freq, uint32_t multiple, int32_t lfo_raw_pm)
;
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
{
	return (value >> start) & ((1 << length) - 1);
}
static uint32_t opl_emu_opl_compute_phase_step(uint32_t block_freq, uint32_t multiple, int32_t lfo_raw_pm)
{
	// OPL phase calculation has no detuning, but uses FNUMs like
	// the OPN version, and computes PM a bit differently

	// extract frequency number as a 12-bit fraction
	uint32_t fnum = opl_emu_bitfield(block_freq, 0, 10) << 2;

	// apply the phase adjustment based on the upper 3 bits
	// of FNUM and the PM depth parameters
	fnum += (lfo_raw_pm * opl_emu_bitfield(block_freq, 7, 3)) >> 1;

	// keep fnum to 12 bits
	fnum &= 0xfff;

	// apply block shift to compute phase step
	uint32_t block = opl_emu_bitfield(block_freq, 10, 3);
	uint32_t phase_step = (fnum << block) >> 2;

	// apply frequency multiplier (which is cached as an x.1 value)
	return (phase_step * multiple) >> 1;
}