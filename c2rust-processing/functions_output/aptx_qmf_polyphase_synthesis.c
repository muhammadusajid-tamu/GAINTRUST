#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 inline void aptx_qmf_polyphase_synthesis(struct aptx_filter_signal signal[NB_FILTERS],
                                                const int32_t coeffs[NB_FILTERS][FILTER_TAPS],
                                                unsigned shift,
                                                int32_t low_subband_input,
                                                int32_t high_subband_input,
                                                int32_t samples[NB_FILTERS])
{
    int32_t subbands[NB_FILTERS];
    unsigned i;

    subbands[0] = low_subband_input + high_subband_input;
    subbands[1] = low_subband_input - high_subband_input;

    for (i = 0; i < NB_FILTERS; i++) {
        aptx_qmf_filter_signal_push(&signal[i], subbands[1-i]);
        samples[i] = aptx_qmf_convolution(&signal[i], coeffs[i], shift);
    }
}