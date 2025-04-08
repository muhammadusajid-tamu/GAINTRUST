#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_decode_channel(struct aptx_channel *channel, int32_t samples[4])
{
    int32_t subband_samples[NB_SUBBANDS];
    unsigned subband;

    for (subband = 0; subband < NB_SUBBANDS; subband++)
        subband_samples[subband] = channel->prediction[subband].previous_reconstructed_sample;
    aptx_qmf_tree_synthesis(&channel->qmf, subband_samples, samples);
}