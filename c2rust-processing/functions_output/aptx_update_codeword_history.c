#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"


 inline void aptx_update_codeword_history(struct aptx_channel *channel)
{
    const int32_t cw = ((channel->quantize[0].quantized_sample & 3) << 0) +
                       ((channel->quantize[1].quantized_sample & 2) << 1) +
                       ((channel->quantize[2].quantized_sample & 1) << 3);
    channel->codeword_history = (cw << 8) + (int32_t)((uint32_t)channel->codeword_history << 4);
}