#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

void aptx_finish(struct aptx_context *ctx)
{
    free(ctx);
}