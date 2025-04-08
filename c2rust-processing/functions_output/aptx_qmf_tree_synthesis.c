#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 void aptx_qmf_tree_synthesis(struct aptx_QMF_analysis *qmf,
                                    const int32_t subband_samples[NB_SUBBANDS],
                                    int32_t samples[4])
{
    int32_t intermediate_samples[4];
    unsigned i;

    /* Join 4 subbands into 2 intermediate subbands upsampled to 2 samples. */
    for (i = 0; i < 2; i++)
        aptx_qmf_polyphase_synthesis(qmf->inner_filter_signal[i],
                                     aptx_qmf_inner_coeffs, 22,
                                     subband_samples[2*i+0],
                                     subband_samples[2*i+1],
                                     &intermediate_samples[2*i]);

    /* Join 2 samples from intermediate subbands upsampled to 4 samples. */
    for (i = 0; i < 2; i++)
        aptx_qmf_polyphase_synthesis(qmf->outer_filter_signal,
                                     aptx_qmf_outer_coeffs, 21,
                                     intermediate_samples[0+i],
                                     intermediate_samples[2+i],
                                     &samples[2*i]);
}