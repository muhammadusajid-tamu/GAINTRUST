#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */

#define OPL_EMU_REGISTERS_WAVEFORMS 8

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
	struct opl_emu_registers* m_regs;                  // direct reference to registers
};
void opl_emu_fm_operator_start_release(struct opl_emu_fm_operator* fmop)
;
void opl_emu_fm_operator_start_attack(struct opl_emu_fm_operator* fmop)
;
void opl_emu_fm_operator_clock_keystate(struct opl_emu_fm_operator* fmop, uint32_t keystate)
;
void opl_emu_fm_operator_start_release(struct opl_emu_fm_operator* fmop)
{
	// don't change anything if already in release state
	if (fmop->m_env_state >= OPL_EMU_EG_RELEASE)
		return;
	fmop->m_env_state = OPL_EMU_EG_RELEASE;
}
void opl_emu_fm_operator_start_attack(struct opl_emu_fm_operator* fmop)
{
	// don't change anything if already in attack state
	if (fmop->m_env_state == OPL_EMU_EG_ATTACK)
		return;
	fmop->m_env_state = OPL_EMU_EG_ATTACK;

	// reset the phase when we start an attack due to a key on
    fmop->m_phase = 0;

	// if the attack rate >= 62 then immediately go to max attenuation
	if (fmop->m_cache.eg_rate[OPL_EMU_EG_ATTACK] >= 62)
		fmop->m_env_attenuation = 0;
}
void opl_emu_fm_operator_clock_keystate(struct opl_emu_fm_operator* fmop, uint32_t keystate)
{
	// has the key changed?
	if ((keystate ^ fmop->m_key_state) != 0)
	{
		fmop->m_key_state = keystate;

		// if the key has turned on, start the attack
		if (keystate != 0)
		{
            opl_emu_fm_operator_start_attack(fmop);
		}

		// otherwise, start the release
		else
			opl_emu_fm_operator_start_release(fmop);
	}
}