#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */

#define opl_min(a,b) (((a)<(b))?(a):(b))





uint32_t opl_emu_registers_effective_rate(uint32_t rawrate, uint32_t ksr)
;
uint32_t opl_emu_registers_effective_rate(uint32_t rawrate, uint32_t ksr)
{
	return (rawrate == 0) ? 0 : opl_min(rawrate + ksr, 63);
}