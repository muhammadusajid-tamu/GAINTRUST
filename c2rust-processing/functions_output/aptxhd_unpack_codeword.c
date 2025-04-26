#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptxhd_unpack_codeword(struct aptx_channel *channel, uint32_t codeword)
{
    channel->quantize[0].quantized_sample = sign_extend((int32_t)(codeword >>  0), 9);
    channel->quantize[1].quantized_sample = sign_extend((int32_t)(codeword >>  9), 6);
    channel->quantize[2].quantized_sample = sign_extend((int32_t)(codeword >> 15), 4);
    channel->quantize[3].quantized_sample = sign_extend((int32_t)(codeword >> 19), 5);
    channel->quantize[3].quantized_sample = (channel->quantize[3].quantized_sample & ~1)
                                          | aptx_quantized_parity(channel);
}