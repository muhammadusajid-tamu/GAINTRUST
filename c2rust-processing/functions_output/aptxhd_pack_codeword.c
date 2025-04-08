#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 uint32_t aptxhd_pack_codeword(const struct aptx_channel *channel)
{
    const int32_t parity = aptx_quantized_parity(channel);
    return (uint32_t)((((channel->quantize[3].quantized_sample & 0x01E) | parity) << 19)
                    | (((channel->quantize[2].quantized_sample & 0x00F)         ) << 15)
                    | (((channel->quantize[1].quantized_sample & 0x03F)         ) <<  9)
                    | (((channel->quantize[0].quantized_sample & 0x1FF)         ) <<  0));
}