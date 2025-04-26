#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 uint16_t aptx_pack_codeword(const struct aptx_channel *channel)
{
    const int32_t parity = aptx_quantized_parity(channel);
    return (uint16_t)((((channel->quantize[3].quantized_sample & 0x06) | parity) << 13)
                    | (((channel->quantize[2].quantized_sample & 0x03)         ) << 11)
                    | (((channel->quantize[1].quantized_sample & 0x0F)         ) <<  7)
                    | (((channel->quantize[0].quantized_sample & 0x7F)         ) <<  0));
}