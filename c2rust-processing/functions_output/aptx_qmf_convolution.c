#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 inline int32_t aptx_qmf_convolution(const struct aptx_filter_signal *signal,
                                           const int32_t coeffs[FILTER_TAPS],
                                           unsigned shift)
{
    const int32_t *sig = &signal->buffer[signal->pos];
    int64_t e = 0;
    unsigned i;

    for (i = 0; i < FILTER_TAPS; i++)
        e += (int64_t)sig[i] * (int64_t)coeffs[i];

    return rshift64_clip24(e, shift);
}