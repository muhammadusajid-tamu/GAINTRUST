#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

void aptx_reset(struct aptx_context *ctx)
{
    const uint8_t hd = ctx->hd;
    unsigned i, chan, subband;
    struct aptx_channel *channel;
    struct aptx_prediction *prediction;

    for (i = 0; i < sizeof(*ctx); i++)
        ((unsigned char *)ctx)[i] = 0;

    ctx->hd = hd;
    ctx->decode_skip_leading = (LATENCY_SAMPLES+3)/4;
    ctx->encode_remaining = (LATENCY_SAMPLES+3)/4;

    for (chan = 0; chan < NB_CHANNELS; chan++) {
        channel = &ctx->channels[chan];
        for (subband = 0; subband < NB_SUBBANDS; subband++) {
            prediction = &channel->prediction[subband];
            prediction->prev_sign[0] = 1;
            prediction->prev_sign[1] = 1;
        }
    }
}