#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






uint32_t opl_emu_registers_operator_list(uint8_t o1, uint8_t o2, uint8_t o3, uint8_t o4)
;
uint32_t opl_emu_registers_operator_list(uint8_t o1, uint8_t o2, uint8_t o3, uint8_t o4)
{
	return o1 | (o2 << 8) | (o3 << 16) | (o4 << 24);
}