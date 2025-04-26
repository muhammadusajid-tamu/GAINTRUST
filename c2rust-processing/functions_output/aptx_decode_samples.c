#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 int aptx_decode_samples(struct aptx_context *ctx,
                                const uint8_t *input,
                                int32_t samples[NB_CHANNELS][4])
{
    unsigned channel;
    int ret;

    for (channel = 0; channel < NB_CHANNELS; channel++) {
        aptx_generate_dither(&ctx->channels[channel]);

        if (ctx->hd)
            aptxhd_unpack_codeword(&ctx->channels[channel],
                                   ((uint32_t)input[3*channel+0] << 16) |
                                   ((uint32_t)input[3*channel+1] <<  8) |
                                   ((uint32_t)input[3*channel+2] <<  0));
        else
            aptx_unpack_codeword(&ctx->channels[channel], (uint16_t)(
                                 ((uint16_t)input[2*channel+0] << 8) |
                                 ((uint16_t)input[2*channel+1] << 0)));
        aptx_invert_quantize_and_prediction(&ctx->channels[channel], ctx->hd);
    }

    ret = aptx_check_parity(ctx->channels, &ctx->sync_idx);

    for (channel = 0; channel < NB_CHANNELS; channel++)
        aptx_decode_channel(&ctx->channels[channel], samples[channel]);

    return ret;
}