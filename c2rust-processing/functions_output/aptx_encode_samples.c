#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_encode_samples(struct aptx_context *ctx,
                                int32_t samples[NB_CHANNELS][4],
                                uint8_t *output)
{
    unsigned channel;
    for (channel = 0; channel < NB_CHANNELS; channel++)
        aptx_encode_channel(&ctx->channels[channel], samples[channel], ctx->hd);

    aptx_insert_sync(ctx->channels, &ctx->sync_idx);

    for (channel = 0; channel < NB_CHANNELS; channel++) {
        aptx_invert_quantize_and_prediction(&ctx->channels[channel], ctx->hd);
        if (ctx->hd) {
            uint32_t codeword = aptxhd_pack_codeword(&ctx->channels[channel]);
            output[3*channel+0] = (uint8_t)((codeword >> 16) & 0xFF);
            output[3*channel+1] = (uint8_t)((codeword >>  8) & 0xFF);
            output[3*channel+2] = (uint8_t)((codeword >>  0) & 0xFF);
        } else {
            uint16_t codeword = aptx_pack_codeword(&ctx->channels[channel]);
            output[2*channel+0] = (uint8_t)((codeword >> 8) & 0xFF);
            output[2*channel+1] = (uint8_t)((codeword >> 0) & 0xFF);
        }
    }
}