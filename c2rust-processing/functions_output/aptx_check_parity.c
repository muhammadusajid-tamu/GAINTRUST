#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 int aptx_check_parity(const struct aptx_channel channels[NB_CHANNELS], uint8_t *sync_idx)
{
    const int32_t parity = aptx_quantized_parity(&channels[LEFT])
                         ^ aptx_quantized_parity(&channels[RIGHT]);
    const int32_t eighth = *sync_idx == 7;

    *sync_idx = (*sync_idx + 1) & 7;
    return parity ^ eighth;
}