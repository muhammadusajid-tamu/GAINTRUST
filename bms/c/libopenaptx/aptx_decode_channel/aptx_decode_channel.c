#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define NB_FILTERS 2

#define NB_SUBBANDS 4

#define FILTER_TAPS 16



static const int32_t aptx_qmf_inner_coeffs[NB_FILTERS][FILTER_TAPS] = {
    {
       1033, -584, -13592, 61697, -171156, 381799, -828088, 3962579,
       985888, -226954, 39048, 11990, -14203, 4966, 973, -1268,
    },
    {
      -1268, 973, 4966, -14203, 11990, 39048, -226954, 985888,
      3962579, -828088, 381799, -171156, 61697, -13592, -584, 1033,
    },
};
static const int32_t aptx_qmf_outer_coeffs[NB_FILTERS][FILTER_TAPS] = {
    {
        730, -413, -9611, 43626, -121026, 269973, -585547, 2801966,
        697128, -160481, 27611, 8478, -10043, 3511, 688, -897,
    },
    {
        -897, 688, 3511, -10043, 8478, 27611, -160481, 697128,
        2801966, -585547, 269973, -121026, 43626, -9611, -413, 730,
    },
};
struct aptx_filter_signal {
    int32_t buffer[2*FILTER_TAPS];
    uint8_t pos;
};
struct aptx_prediction {
    int32_t prev_sign[2];
    int32_t s_weight[2];
    int32_t d_weight[24];
    int32_t pos;
    int32_t reconstructed_differences[48];
    int32_t previous_reconstructed_sample;
    int32_t predicted_difference;
    int32_t predicted_sample;
};
struct aptx_invert_quantize {
    int32_t quantization_factor;
    int32_t factor_select;
    int32_t reconstructed_difference;
};
struct aptx_quantize {
    int32_t quantized_sample;
    int32_t quantized_sample_parity_change;
    int32_t error;
};
struct aptx_QMF_analysis {
    struct aptx_filter_signal outer_filter_signal[NB_FILTERS];
    struct aptx_filter_signal inner_filter_signal[NB_FILTERS][NB_FILTERS];
};
struct aptx_channel {
    int32_t codeword_history;
    int32_t dither_parity;
    int32_t dither[NB_SUBBANDS];

    struct aptx_QMF_analysis qmf;
    struct aptx_quantize quantize[NB_SUBBANDS];
    struct aptx_invert_quantize invert_quantize[NB_SUBBANDS];
    struct aptx_prediction prediction[NB_SUBBANDS];
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
static void aptx_qmf_tree_synthesis(struct aptx_QMF_analysis *qmf,
                                    const int32_t subband_samples[NB_SUBBANDS],
                                    int32_t samples[4])
;
static void aptx_decode_channel(struct aptx_channel *channel, int32_t samples[4])
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
static void aptx_qmf_tree_synthesis(struct aptx_QMF_analysis *qmf,
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
static void aptx_decode_channel(struct aptx_channel *channel, int32_t samples[4])
{
    int32_t subband_samples[NB_SUBBANDS];
    unsigned subband;

    for (subband = 0; subband < NB_SUBBANDS; subband++)
        subband_samples[subband] = channel->prediction[subband].previous_reconstructed_sample;
    aptx_qmf_tree_synthesis(&channel->qmf, subband_samples, samples);
}