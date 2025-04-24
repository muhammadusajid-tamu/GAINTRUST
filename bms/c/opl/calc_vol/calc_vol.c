#include <stdio.h>

#include <stdint.h>

#include <stdlib.h> /* calloc() */

#include <string.h> /* strdup() */






static void calc_vol(unsigned char *regbyte, int volume) ;
static void calc_vol(unsigned char *regbyte, int volume) {
  int level;
  /* invert bits and strip out the KSL header */
  level = ~(*regbyte);
  level &= 0x3f;

  /* adjust volume */
  level = (level * volume) / 127;

  /* boundaries check */
  if (level > 0x3f) level = 0x3f;
  if (level < 0) level = 0;

  /* invert the bits, as expected by the OPL registers */
  level = ~level;
  level &= 0x3f;

  /* final result computation */
  *regbyte &= 0xC0;  /* zero out all attentuation bits */
  *regbyte |= level; /* fill in the new attentuation value */
}