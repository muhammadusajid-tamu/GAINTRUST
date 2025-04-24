#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






uint32_t opl_emu_registers_operator_offset(uint32_t opnum)
;
uint32_t opl_emu_registers_operator_offset(uint32_t opnum)
{
    return (opnum % 18) + 2 * ((opnum % 18) / 6) + 0x100 * (opnum / 18);
}