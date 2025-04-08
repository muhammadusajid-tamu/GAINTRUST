#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

size_t aptx_encode(struct aptx_context *ctx, const unsigned char *input, size_t input_size, unsigned char *output, size_t output_size, size_t *written)
{
    const size_t sample_size = ctx->hd ? 6 : 4;
    int32_t samples[NB_CHANNELS][4];
    unsigned sample, channel;
    size_t ipos, opos;

    for (ipos = 0, opos = 0; ipos + 3*NB_CHANNELS*4 <= input_size && opos + sample_size <= output_size; opos += sample_size) {
        for (sample = 0; sample < 4; sample++) {
            for (channel = 0; channel < NB_CHANNELS; channel++, ipos += 3) {
                /* samples need to contain 24bit signed integer stored as 32bit signed integers */
                /* last int8_t --> uint32_t cast propagates signedness for 32bit integer */
                samples[channel][sample] = (int32_t)(((uint32_t)input[ipos+0] << 0) |
                                                     ((uint32_t)input[ipos+1] << 8) |
                                                     ((uint32_t)(int8_t)input[ipos+2] << 16));
            }
        }
        aptx_encode_samples(ctx, samples, output + opos);
    }

    *written = opos;
    return ipos;
}