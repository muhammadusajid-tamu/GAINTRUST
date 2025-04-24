#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






uint32_t opl_emu_registers_channel_offset(uint32_t chnum)
;
uint32_t opl_emu_registers_channel_offset(uint32_t chnum)
{
    return (chnum % 9) + 0x100 * (chnum / 9);
}