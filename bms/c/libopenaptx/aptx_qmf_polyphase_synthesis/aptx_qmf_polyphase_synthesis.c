#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define NB_FILTERS 2

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
static inline void aptx_qmf_filter_signal_push(struct aptx_filter_signal *signal,
                                               int32_t sample)
;
static inline void aptx_qmf_polyphase_synthesis(struct aptx_filter_signal signal[NB_FILTERS],
                                                const int32_t coeffs[NB_FILTERS][FILTER_TAPS],
                                                unsigned shift,
                                                int32_t low_subband_input,
                                                int32_t high_subband_input,
                                                int32_t samples[NB_FILTERS])
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
static inline void aptx_qmf_filter_signal_push(struct aptx_filter_signal *signal,
                                               int32_t sample)
{
    signal->buffer[signal->pos            ] = sample;
    signal->buffer[signal->pos+FILTER_TAPS] = sample;
    signal->pos = (signal->pos + 1) & (FILTER_TAPS - 1);
}
static inline void aptx_qmf_polyphase_synthesis(struct aptx_filter_signal signal[NB_FILTERS],
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