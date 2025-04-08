#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_insert_sync(struct aptx_channel channels[NB_CHANNELS], uint8_t *sync_idx)
{
    unsigned i;
    struct aptx_channel *c;
     const unsigned map[] = { 1, 2, 0, 3 };
    struct aptx_quantize *min = &channels[NB_CHANNELS-1].quantize[map[0]];

    if (aptx_check_parity(channels, sync_idx)) {
        for (c = &channels[NB_CHANNELS-1]; c >= channels; c--)
            for (i = 0; i < NB_SUBBANDS; i++)
                if (c->quantize[map[i]].error < min->error)
                    min = &c->quantize[map[i]];

        /*
         * Forcing the desired parity is done by offsetting by 1 the quantized
         * sample from the subband featuring the smallest quantization error.
         */
        min->quantized_sample = min->quantized_sample_parity_change;
    }
}