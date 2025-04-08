#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_reset_decode_sync(struct aptx_context *ctx)
{
    const size_t decode_dropped = ctx->decode_dropped;
    const size_t decode_sync_packets = ctx->decode_sync_packets;
    const uint8_t decode_sync_buffer_len = ctx->decode_sync_buffer_len;
    unsigned char decode_sync_buffer[6];
    unsigned i;

    for (i = 0; i < 6; i++)
        decode_sync_buffer[i] = ctx->decode_sync_buffer[i];

    aptx_reset(ctx);

    for (i = 0; i < 6; i++)
        ctx->decode_sync_buffer[i] = decode_sync_buffer[i];

    ctx->decode_sync_buffer_len = decode_sync_buffer_len;
    ctx->decode_sync_packets = decode_sync_packets;
    ctx->decode_dropped = decode_dropped;
}