#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_generate_dither(struct aptx_channel *channel)
{
    unsigned subband;
    int64_t m;
    int32_t d;

    aptx_update_codeword_history(channel);

    m = (int64_t)5184443 * (channel->codeword_history >> 7);
    d = (int32_t)((m * 4) + (m >> 22));
    for (subband = 0; subband < NB_SUBBANDS; subband++)
        channel->dither[subband] = (int32_t)((uint32_t)d << (23 - 5*subband));
    channel->dither_parity = (d >> 25) & 1;
}