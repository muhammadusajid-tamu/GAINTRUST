#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */

#define OPL_EMU_REGISTERS_CHANNELS 18

#define OPL_EMU_REGISTERS_WAVEFORM_LENGTH 0x400

#define OPL_EMU_REGISTERS_REGISTERS 0x200

#define OPL_EMU_REGISTERS_WAVEFORMS 8




struct opl_emu_registers_operator_mapping { uint32_t chan[OPL_EMU_REGISTERS_CHANNELS]; };
struct opl_emu_registers
{
	// internal state
	uint16_t m_lfo_am_counter;            // LFO AM counter
	uint16_t m_lfo_pm_counter;            // LFO PM counter
	uint32_t m_noise_lfsr;                // noise LFSR state
	uint8_t m_lfo_am;                     // current LFO AM value
	uint8_t m_regdata[OPL_EMU_REGISTERS_REGISTERS];         // register data
	uint16_t m_waveform[OPL_EMU_REGISTERS_WAVEFORMS][OPL_EMU_REGISTERS_WAVEFORM_LENGTH]; // waveforms
};
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
;
uint32_t opl_emu_registers_byte(struct opl_emu_registers* regs,uint32_t offset, uint32_t start, uint32_t count, uint32_t extra_offset/* = 0*/) 
;
uint32_t opl_emu_registers_operator_list(uint8_t o1, uint8_t o2, uint8_t o3, uint8_t o4)
;
uint32_t opl_emu_registers_fourop_enable(struct opl_emu_registers* regs)                    ;
void opl_emu_registers_operator_map(struct opl_emu_registers* regs, struct opl_emu_registers_operator_mapping* dest)
;
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
{
	return (value >> start) & ((1 << length) - 1);
}
uint32_t opl_emu_registers_byte(struct opl_emu_registers* regs,uint32_t offset, uint32_t start, uint32_t count, uint32_t extra_offset/* = 0*/) 
{
	return opl_emu_bitfield(regs->m_regdata[offset + extra_offset], start, count);
}
uint32_t opl_emu_registers_operator_list(uint8_t o1, uint8_t o2, uint8_t o3, uint8_t o4)
{
	return o1 | (o2 << 8) | (o3 << 16) | (o4 << 24);
}
uint32_t opl_emu_registers_fourop_enable(struct opl_emu_registers* regs)                    { return opl_emu_registers_byte(regs,0x104, 0, 6, 0); }
void opl_emu_registers_operator_map(struct opl_emu_registers* regs, struct opl_emu_registers_operator_mapping* dest)
{
    // OPL3/OPL4 can be configured for 2 or 4 operators
    uint32_t fourop = opl_emu_registers_fourop_enable(regs);

    dest->chan[ 0] = opl_emu_bitfield(fourop, 0,1) ? opl_emu_registers_operator_list(  0,  3,  6,  9 ) : opl_emu_registers_operator_list(  0,  3, 0xff, 0xff );
    dest->chan[ 1] = opl_emu_bitfield(fourop, 1,1) ? opl_emu_registers_operator_list(  1,  4,  7, 10 ) : opl_emu_registers_operator_list(  1,  4, 0xff, 0xff );
    dest->chan[ 2] = opl_emu_bitfield(fourop, 2,1) ? opl_emu_registers_operator_list(  2,  5,  8, 11 ) : opl_emu_registers_operator_list(  2,  5, 0xff, 0xff );
    dest->chan[ 3] = opl_emu_bitfield(fourop, 0,1) ? opl_emu_registers_operator_list( 0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list(  6,  9, 0xff, 0xff );
    dest->chan[ 4] = opl_emu_bitfield(fourop, 1,1) ? opl_emu_registers_operator_list( 0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list(  7, 10, 0xff, 0xff );
    dest->chan[ 5] = opl_emu_bitfield(fourop, 2,1) ? opl_emu_registers_operator_list( 0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list(  8, 11, 0xff, 0xff );
    dest->chan[ 6] = opl_emu_registers_operator_list( 12, 15, 0xff, 0xff );
    dest->chan[ 7] = opl_emu_registers_operator_list( 13, 16, 0xff, 0xff );
    dest->chan[ 8] = opl_emu_registers_operator_list( 14, 17, 0xff, 0xff );

    dest->chan[ 9] = opl_emu_bitfield(fourop, 3,1) ? opl_emu_registers_operator_list( 18, 21, 24, 27 ) : opl_emu_registers_operator_list( 18, 21, 0xff, 0xff );
    dest->chan[10] = opl_emu_bitfield(fourop, 4,1) ? opl_emu_registers_operator_list( 19, 22, 25, 28 ) : opl_emu_registers_operator_list( 19, 22, 0xff, 0xff );
    dest->chan[11] = opl_emu_bitfield(fourop, 5,1) ? opl_emu_registers_operator_list( 20, 23, 26, 29 ) : opl_emu_registers_operator_list( 20, 23, 0xff, 0xff );
    dest->chan[12] = opl_emu_bitfield(fourop, 3,1) ? opl_emu_registers_operator_list(0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list( 24, 27, 0xff, 0xff );
    dest->chan[13] = opl_emu_bitfield(fourop, 4,1) ? opl_emu_registers_operator_list(0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list( 25, 28, 0xff, 0xff );
    dest->chan[14] = opl_emu_bitfield(fourop, 5,1) ? opl_emu_registers_operator_list(0xff, 0xff, 0xff, 0xff) : opl_emu_registers_operator_list( 26, 29, 0xff, 0xff );
    dest->chan[15] = opl_emu_registers_operator_list( 30, 33, 0xff, 0xff );
    dest->chan[16] = opl_emu_registers_operator_list( 31, 34, 0xff, 0xff );
    dest->chan[17] = opl_emu_registers_operator_list( 32, 35, 0xff, 0xff );
}