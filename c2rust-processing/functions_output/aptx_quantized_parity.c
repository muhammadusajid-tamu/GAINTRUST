#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 int32_t aptx_quantized_parity(const struct aptx_channel *channel)
{
    int32_t parity = channel->dither_parity;
    unsigned subband;

    for (subband = 0; subband < NB_SUBBANDS; subband++)
        parity ^= channel->quantize[subband].quantized_sample;

    return parity & 1;
}