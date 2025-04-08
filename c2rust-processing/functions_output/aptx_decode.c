#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

size_t aptx_decode(struct aptx_context *ctx, const unsigned char *input, size_t input_size, unsigned char *output, size_t output_size, size_t *written)
{
    const size_t sample_size = ctx->hd ? 6 : 4;
    int32_t samples[NB_CHANNELS][4];
    unsigned sample, channel;
    size_t ipos, opos;

    for (ipos = 0, opos = 0; ipos + sample_size <= input_size && (opos + 3*NB_CHANNELS*4 <= output_size || ctx->decode_skip_leading > 0); ipos += sample_size) {
        if (aptx_decode_samples(ctx, input + ipos, samples))
            break;
        sample = 0;
        if (ctx->decode_skip_leading > 0) {
            ctx->decode_skip_leading--;
            if (ctx->decode_skip_leading > 0)
                continue;
            sample = LATENCY_SAMPLES%4;
        }
        for (; sample < 4; sample++) {
            for (channel = 0; channel < NB_CHANNELS; channel++, opos += 3) {
                /* samples contain 24bit signed integers stored as 32bit signed integers */
                /* we do not need to care about negative integers specially as they have 23th bit set */
                output[opos+0] = (uint8_t)(((uint32_t)samples[channel][sample] >>  0) & 0xFF);
                output[opos+1] = (uint8_t)(((uint32_t)samples[channel][sample] >>  8) & 0xFF);
                output[opos+2] = (uint8_t)(((uint32_t)samples[channel][sample] >> 16) & 0xFF);
            }
        }
    }

    *written = opos;
    return ipos;
}