#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_encode_channel(struct aptx_channel *channel, const int32_t samples[4], int hd)
{
    int32_t subband_samples[NB_SUBBANDS];
    int32_t diff;
    unsigned subband;

    aptx_qmf_tree_analysis(&channel->qmf, samples, subband_samples);
    aptx_generate_dither(channel);

    for (subband = 0; subband < NB_SUBBANDS; subband++) {
        diff = clip_intp2(subband_samples[subband] - channel->prediction[subband].predicted_sample, 23);
        aptx_quantize_difference(&channel->quantize[subband], diff,
                                 channel->dither[subband],
                                 channel->invert_quantize[subband].quantization_factor,
                                 &all_tables[hd][subband]);
    }
}