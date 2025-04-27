#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define FILTER_TAPS 16




struct aptx_filter_signal {
    int32_t buffer[2*FILTER_TAPS];
    uint8_t pos;
};
static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int64_t rshift64(int64_t value, unsigned shift) ;
static inline int32_t rshift64_clip24(int64_t value, unsigned shift) ;
static inline int32_t aptx_qmf_convolution(const struct aptx_filter_signal *signal,
                                           const int32_t coeffs[FILTER_TAPS],
                                           unsigned shift)
;
static inline int32_t clip_intp2(int32_t a, unsigned p)
{
    if (((uint32_t)a + ((uint32_t)1 << p)) & ~(((uint32_t)2 << p) - 1))
        return (a >> 31) ^ ((1 << p) - 1);
    else
        return a;
}
static inline int64_t rshift64(int64_t value, unsigned shift) { const int64_t rounding = (int64_t)1 << (shift - 1); const int64_t mask = ((int64_t)1 << (shift + 1)) - 1; return ((value + rounding) >> shift) - ((value & mask) == rounding); }
static inline int32_t rshift64_clip24(int64_t value, unsigned shift) { return clip_intp2((int32_t)rshift64(value, shift), 23); }
static inline int32_t aptx_qmf_convolution(const struct aptx_filter_signal *signal,
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