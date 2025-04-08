#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

size_t aptx_decode_sync_finish(struct aptx_context *ctx)
{
    const uint8_t dropped = ctx->decode_sync_buffer_len;
    aptx_reset(ctx);
    return dropped;
}