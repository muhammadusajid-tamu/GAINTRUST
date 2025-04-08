#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

size_t aptx_decode_sync(struct aptx_context *ctx, const unsigned char *input, size_t input_size, unsigned char *output, size_t output_size, size_t *written, int *synced, size_t *dropped)
{
    const size_t sample_size = ctx->hd ? 6 : 4;
    size_t input_size_step;
    size_t processed_step;
    size_t written_step;
    size_t ipos = 0;
    size_t opos = 0;
    size_t i;

    *synced = 0;
    *dropped = 0;

    /* If we have some unprocessed bytes in internal cache, first fill remaining data to internal cache except the final byte */
    if (ctx->decode_sync_buffer_len > 0 && sample_size-1 - ctx->decode_sync_buffer_len <= input_size) {
        while (ctx->decode_sync_buffer_len < sample_size-1)
            ctx->decode_sync_buffer[ctx->decode_sync_buffer_len++] = input[ipos++];
    }

    /* Internal cache decode loop, use it only when sample is split between internal cache and input buffer */
    while (ctx->decode_sync_buffer_len == sample_size-1 && ipos < sample_size && ipos < input_size && (opos + 3*NB_CHANNELS*4 <= output_size || ctx->decode_skip_leading > 0 || ctx->decode_dropped > 0)) {
        ctx->decode_sync_buffer[sample_size-1] = input[ipos++];

        processed_step = aptx_decode(ctx, ctx->decode_sync_buffer, sample_size, output + opos, output_size - opos, &written_step);

        opos += written_step;

        if (ctx->decode_dropped > 0 && processed_step == sample_size) {
            ctx->decode_dropped += processed_step;
            ctx->decode_sync_packets++;
            if (ctx->decode_sync_packets >= (LATENCY_SAMPLES+3)/4) {
                *dropped += ctx->decode_dropped;
                ctx->decode_dropped = 0;
                ctx->decode_sync_packets = 0;
            }
        }

        if (processed_step < sample_size) {
            aptx_reset_decode_sync(ctx);
            *synced = 0;
            ctx->decode_dropped++;
            ctx->decode_sync_packets = 0;
            for (i = 0; i < sample_size-1; i++)
                ctx->decode_sync_buffer[i] = ctx->decode_sync_buffer[i+1];
        } else {
            if (ctx->decode_dropped == 0)
                *synced = 1;
            ctx->decode_sync_buffer_len = 0;
        }
    }

    /* If all unprocessed data are now available only in input buffer, do not use internal cache */
    if (ctx->decode_sync_buffer_len == sample_size-1 && ipos == sample_size) {
        ipos = 0;
        ctx->decode_sync_buffer_len = 0;
    }

    /* Main decode loop, decode as much as possible samples, if decoding fails restart it on next byte */
    while (ipos + sample_size <= input_size && (opos + 3*NB_CHANNELS*4 <= output_size || ctx->decode_skip_leading > 0 || ctx->decode_dropped > 0)) {
        input_size_step = (((output_size - opos) / 3*NB_CHANNELS*4) + ctx->decode_skip_leading) * sample_size;
        if (input_size_step > ((input_size - ipos) / sample_size) * sample_size)
            input_size_step = ((input_size - ipos) / sample_size) * sample_size;
        if (input_size_step > ((LATENCY_SAMPLES+3)/4 - ctx->decode_sync_packets) * sample_size && ctx->decode_dropped > 0)
            input_size_step = ((LATENCY_SAMPLES+3)/4 - ctx->decode_sync_packets) * sample_size;

        processed_step = aptx_decode(ctx, input + ipos, input_size_step, output + opos, output_size - opos, &written_step);

        ipos += processed_step;
        opos += written_step;

        if (ctx->decode_dropped > 0 && processed_step / sample_size > 0) {
            ctx->decode_dropped += processed_step;
            ctx->decode_sync_packets += processed_step / sample_size;
            if (ctx->decode_sync_packets >= (LATENCY_SAMPLES+3)/4) {
                *dropped += ctx->decode_dropped;
                ctx->decode_dropped = 0;
                ctx->decode_sync_packets = 0;
            }
        }

        if (processed_step < input_size_step) {
            aptx_reset_decode_sync(ctx);
            *synced = 0;
            ipos++;
            ctx->decode_dropped++;
            ctx->decode_sync_packets = 0;
        } else if (ctx->decode_dropped == 0) {
            *synced = 1;
        }
    }

    /* If number of unprocessed bytes is less then sample size store them to internal cache */
    if (ipos + sample_size > input_size) {
        while (ipos < input_size)
            ctx->decode_sync_buffer[ctx->decode_sync_buffer_len++] = input[ipos++];
    }

    *written = opos;
    return ipos;
}