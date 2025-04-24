#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */

#define OPL_EMU_REGISTERS_OPERATORS ( OPL_EMU_REGISTERS_CHANNELS * 2 )

#define OPL_EMU_REGISTERS_WAVEFORMS 8

#define OPL_EMU_REGISTERS_CHANNELS 18

#define OPL_EMU_REGISTERS_REGISTERS 0x200

#define OPL_EMU_REGISTERS_WAVEFORM_LENGTH 0x400

enum opl_emu_envelope_state
{
	OPL_EMU_EG_ATTACK = 1,
	OPL_EMU_EG_DECAY = 2,
	OPL_EMU_EG_SUSTAIN = 3,
	OPL_EMU_EG_RELEASE = 4,
	OPL_EMU_EG_STATES = 6
};


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
struct opl_emu_opdata_cache
{
	// set phase_step to this value to recalculate it each sample; needed
	// in the case of PM LFO changes

	uint32_t phase_step;              // phase step, or OPL_EMU_PHASE_STEP_DYNAMIC if PM is active
	uint32_t total_level;             // total level * 8 + KSL
	uint32_t block_freq;              // raw block frequency value (used to compute phase_step)
	int32_t detune;                   // detuning value (used to compute phase_step)
	uint32_t multiple;                // multiple value (x.1, used to compute phase_step)
	uint32_t eg_sustain;              // sustain level, shifted up to envelope values
	uint8_t eg_rate[OPL_EMU_EG_STATES];       // envelope rate, including KSR
	uint8_t eg_shift;                 // envelope shift amount
};
struct opl_emu_fm_operator
{
	// internal state
	uint32_t m_choffs;                     // channel offset in registers
	uint32_t m_opoffs;                     // operator offset in registers
	uint32_t m_phase;                      // current phase value (10.10 format)
	uint16_t m_env_attenuation;            // computed envelope attenuation (4.6 format)
	enum opl_emu_envelope_state m_env_state;            // current envelope state
	uint8_t m_key_state;                   // current key state: on or off (bit 0)
	uint8_t m_keyon_live;                  // live key on state (bit 0 = direct, bit 1 = rhythm, bit 2 = CSM)
	struct opl_emu_opdata_cache m_cache;                  // cached values for performance
};
struct opl_emu_fm_channel
{
	// internal state
	uint32_t m_choffs;                     // channel offset in registers
	int16_t m_feedback[2];                 // feedback memory for operator 1
	int16_t m_feedback_in;         // next input value for op 1 feedback (set in output)
};
struct opl_emu_t
{
	uint32_t m_env_counter;          // envelope counter; low 2 bits are sub-counter
	uint8_t m_status;                // current status register
	uint8_t m_timer_running[2];      // current timer running state
	uint32_t m_active_channels;      // mask of active channels (computed by prepare)
	uint32_t m_modified_channels;    // mask of channels that have been modified
	uint32_t m_prepare_count;        // counter to do periodic prepare sweeps
	struct opl_emu_registers m_regs;             // register accessor
	struct opl_emu_fm_channel m_channel[OPL_EMU_REGISTERS_CHANNELS]; // channel pointers
	struct opl_emu_fm_operator m_operator[OPL_EMU_REGISTERS_OPERATORS]; // operator pointers
};
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
;
uint32_t opl_emu_registers_byte(struct opl_emu_registers* regs,uint32_t offset, uint32_t start, uint32_t count, uint32_t extra_offset/* = 0*/) 
;
uint32_t opl_emu_registers_timer_b_value(struct opl_emu_registers* regs)                    ;
uint32_t opl_emu_registers_timer_a_value(struct opl_emu_registers* regs)                    ;
void opl_emu_update_timer( struct opl_emu_t* emu, uint32_t tnum, uint32_t enable)
;
uint32_t opl_emu_bitfield(uint32_t value, int start, int length )
{
	return (value >> start) & ((1 << length) - 1);
}
uint32_t opl_emu_registers_byte(struct opl_emu_registers* regs,uint32_t offset, uint32_t start, uint32_t count, uint32_t extra_offset/* = 0*/) 
{
	return opl_emu_bitfield(regs->m_regdata[offset + extra_offset], start, count);
}
uint32_t opl_emu_registers_timer_b_value(struct opl_emu_registers* regs)                    { return opl_emu_registers_byte(regs,0x03, 0, 8, 0); }
uint32_t opl_emu_registers_timer_a_value(struct opl_emu_registers* regs)                    { return opl_emu_registers_byte(regs,0x02, 0, 8, 0) * 4; }
void opl_emu_update_timer( struct opl_emu_t* emu, uint32_t tnum, uint32_t enable)
{
	// if the timer is live, but not currently enabled, set the timer
	if (enable && !emu->m_timer_running[tnum])
	{
		// period comes from the registers, and is different for each
		uint32_t period = (tnum == 0) ? (1024 - opl_emu_registers_timer_a_value(&emu->m_regs)) : 16 * (256 - opl_emu_registers_timer_b_value(&emu->m_regs));

		// reset it
		//emu->m_intf.opl_emu_set_timer(tnum, period * OPERATORS * emu->m_clock_prescale);
		emu->m_timer_running[tnum] = 1;
	}

	// if the timer is not live, ensure it is not enabled
	else if (!enable)
	{
		//emu->m_intf.opl_emu_set_timer(tnum, -1);
		emu->m_timer_running[tnum] = 0;
	}
}