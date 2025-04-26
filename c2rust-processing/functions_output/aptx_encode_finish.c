#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

int aptx_encode_finish(struct aptx_context *ctx, unsigned char *output, size_t output_size, size_t *written)
{
    const size_t sample_size = ctx->hd ? 6 : 4;
    int32_t samples[NB_CHANNELS][4] = { { 0 } };
    size_t opos;

    if (ctx->encode_remaining == 0) {
        *written = 0;
        return 1;
    }

    for (opos = 0; ctx->encode_remaining > 0 && opos + sample_size <= output_size; ctx->encode_remaining--, opos += sample_size)
        aptx_encode_samples(ctx, samples, output + opos);

    *written = opos;

    if (ctx->encode_remaining > 0)
        return 0;

    aptx_reset(ctx);
    return 1;
}