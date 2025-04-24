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
enum op2_flags_t {
  OP2_FIXEDPITCH = 1,
  OP2_UNUSED = 2, /* technically delayed vibrato https://moddingwiki.shikadi.net/wiki/OP2_Bank_Format */
  OP2_DOUBLEVOICE = 4,
};
typedef struct opl_t opl_t;

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
struct opl_emu_fm_channel
{
	// internal state
	uint32_t m_choffs;                     // channel offset in registers
	int16_t m_feedback[2];                 // feedback memory for operator 1
	int16_t m_feedback_in;         // next input value for op 1 feedback (set in output)
	struct opl_emu_fm_operator *m_op[4];    // up to 4 operators
	struct opl_emu_registers* m_regs;                  // direct reference to registers
};
typedef struct opl_timbre_t {
  unsigned long modulator_E862, carrier_E862;
  unsigned char modulator_40, carrier_40;
  unsigned char feedconn;
  signed char finetune;
  unsigned char notenum;
  signed short noteoffset;
} opl_timbre_t;
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
struct voicealloc_t {
  unsigned short priority;
  signed short timbreid;
  signed char channel;
  signed char note;
  unsigned char voiceindex; /* 1 if 2nd voice for OP2 soundbank instrument, 0 otherwise */
};
struct opl_t {
  signed char notes2voices[16][128][2]; /* keeps the map of channel:notes -> voice allocations */
  unsigned short channelpitch[16];      /* per-channel pitch level */
  unsigned short channelvol[16];        /* per-channel pitch level */
  struct voicealloc_t voices2notes[18]; /* keeps the map of what voice is playing what note/channel currently */
  unsigned char channelprog[16];        /* programs (patches) assigned to channels */
  int opl3; /* flag indicating whether or not the sound module is OPL3-compatible or only OPL2 */
  struct opl_emu_t opl_emu;
  struct opl_timbre_t opl_gmtimbres[ 256 ];
  struct opl_timbre_t opl_gmtimbres_voice2[ 256 ]; /* second voice included in OP2 format */
  int is_op2; /* true if OP2 soundbank */
  enum op2_flags_t op2_flags[ 256 ]; /* OP2 format flags */
};
static int getinstrument(opl_t* opl, int channel, int note) ;
static int getinstrument(opl_t* opl, int channel, int note) {
  if ((note < 0) || (note > 127) || (channel > 15)) return(-1);
  if (channel == 9) { /* the percussion channel requires special handling */
    if (opl->is_op2)
      return 128 + note - 35;
    else
      return(128 | note);
  }
  return(opl->channelprog[channel]);
}