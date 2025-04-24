#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */

#define opl_max(a,b) (((a)>(b))?(a):(b))





uint32_t opl_emu_opl_key_scale_atten(uint32_t block, uint32_t fnum_4msb)
;
uint32_t opl_emu_opl_key_scale_atten(uint32_t block, uint32_t fnum_4msb)
{
	// this table uses the top 4 bits of FNUM and are the maximal values
	// (for when block == 7). Values for other blocks can be computed by
	// subtracting 8 for each block below 7.
	static uint8_t const fnum_to_atten[16] = { 0,24,32,37,40,43,45,47,48,50,51,52,53,54,55,56 };
	int32_t result = fnum_to_atten[fnum_4msb] - 8 * (block ^ 7);
	return opl_max(0, result);
}