#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */





typedef struct opl_timbre_t {
  unsigned long modulator_E862, carrier_E862;
  unsigned char modulator_40, carrier_40;
  unsigned char feedconn;
  signed char finetune;
  unsigned char notenum;
  signed short noteoffset;
} opl_timbre_t;
static void opl_load_op2_voice(opl_timbre_t* timbre, uint8_t const* buff) ;
static void opl_load_op2_voice(opl_timbre_t* timbre, uint8_t const* buff) {
  /* load modulator */
  timbre->modulator_E862 = buff[3]; /* wave select */
  timbre->modulator_E862 <<= 8;
  timbre->modulator_E862 |= buff[2]; /* sust/release */
  timbre->modulator_E862 <<= 8;
  timbre->modulator_E862 |= buff[1]; /* attack/decay */
  timbre->modulator_E862 <<= 8;
  timbre->modulator_E862 |= buff[0]; /* AM/VIB... flags */
  /* load carrier */
  timbre->carrier_E862 = buff[10]; /* wave select */
  timbre->carrier_E862 <<= 8;
  timbre->carrier_E862 |= buff[9]; /* sust/release */
  timbre->carrier_E862 <<= 8;
  timbre->carrier_E862 |= buff[8]; /* attack/decay */
  timbre->carrier_E862 <<= 8;
  timbre->carrier_E862 |= buff[7]; /* AM/VIB... flags */
  /* load KSL */
  timbre->modulator_40 = ( buff[5] & 0x3f ) | ( buff[4] & 0xc0 );
  timbre->carrier_40 = ( buff[12] & 0x3f ) | ( buff[11] & 0xc0 );
  /* feedconn & finetune */
  timbre->feedconn = buff[6];
  timbre->finetune = 0;
  timbre->noteoffset = (int16_t)(buff[14] | ((uint16_t)buff[15] << 8));
}