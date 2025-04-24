#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
;
static int32_t opl_emu_opl_clock_noise_and_lfo(uint32_t *noise_lfsr, uint16_t *lfo_am_counter, uint16_t *lfo_pm_counter, uint8_t *lfo_am, uint32_t am_depth, uint32_t pm_depth)
;
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
{
	return (value >> start) & ((1 << length) - 1);
}
static int32_t opl_emu_opl_clock_noise_and_lfo(uint32_t *noise_lfsr, uint16_t *lfo_am_counter, uint16_t *lfo_pm_counter, uint8_t *lfo_am, uint32_t am_depth, uint32_t pm_depth)
{
	// OPL has a 23-bit noise generator for the rhythm section, running at
	// a constant rate, used only for percussion input
	*noise_lfsr <<= 1;
	*noise_lfsr |= opl_emu_bitfield(*noise_lfsr, 23,1) ^ opl_emu_bitfield(*noise_lfsr, 9,1) ^ opl_emu_bitfield(*noise_lfsr, 8,1) ^ opl_emu_bitfield(*noise_lfsr, 1,1);

	// OPL has two fixed-frequency LFOs, one for AM, one for PM

	// the AM LFO has 210*64 steps; at a nominal 50kHz output,
	// this equates to a period of 50000/(210*64) = 3.72Hz
	uint32_t am_counter = *lfo_am_counter++;
	if (am_counter >= 210*64 - 1)
		*lfo_am_counter = 0;

	// low 8 bits are fractional; depth 0 is divided by 2, while depth 1 is times 2
	int shift = 9 - 2 * am_depth;

	// AM value is the upper bits of the value, inverted across the midpoint
	// to produce a triangle
	*lfo_am = ((am_counter < 105*64) ? am_counter : (210*64+63 - am_counter)) >> shift;

	// the PM LFO has 8192 steps, or a nominal period of 6.1Hz
	uint32_t pm_counter = *lfo_pm_counter++;

	// PM LFO is broken into 8 chunks, each lasting 1024 steps; the PM value
	// depends on the upper bits of FNUM, so this value is a fraction and
	// sign to apply to that value, as a 1.3 value
	static int8_t pm_scale[8] = { 8, 4, 0, -4, -8, -4, 0, 4 };
	return pm_scale[opl_emu_bitfield(pm_counter, 10, 3)] >> (pm_depth ^ 1);
}