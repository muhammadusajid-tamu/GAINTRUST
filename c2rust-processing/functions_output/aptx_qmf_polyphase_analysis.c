#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 inline void aptx_qmf_polyphase_analysis(struct aptx_filter_signal signal[NB_FILTERS],
                                               const int32_t coeffs[NB_FILTERS][FILTER_TAPS],
                                               unsigned shift,
                                               const int32_t samples[NB_FILTERS],
                                               int32_t *low_subband_output,
                                               int32_t *high_subband_output)
{
    int32_t subbands[NB_FILTERS];
    unsigned i;

    for (i = 0; i < NB_FILTERS; i++) {
        aptx_qmf_filter_signal_push(&signal[i], samples[NB_FILTERS-1-i]);
        subbands[i] = aptx_qmf_convolution(&signal[i], coeffs[i], shift);
    }

    *low_subband_output  = clip_intp2(subbands[0] + subbands[1], 23);
    *high_subband_output = clip_intp2(subbands[0] - subbands[1], 23);
}