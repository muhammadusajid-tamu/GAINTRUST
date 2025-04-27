#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define NB_FILTERS 2

#define NB_SUBBANDS 4

#define FILTER_TAPS 16




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
static inline void aptx_update_codeword_history(struct aptx_channel *channel)
;
static void aptx_generate_dither(struct aptx_channel *channel)
;
static inline void aptx_update_codeword_history(struct aptx_channel *channel)
{
    const int32_t cw = ((channel->quantize[0].quantized_sample & 3) << 0) +
                       ((channel->quantize[1].quantized_sample & 2) << 1) +
                       ((channel->quantize[2].quantized_sample & 1) << 3);
    channel->codeword_history = (cw << 8) + (int32_t)((uint32_t)channel->codeword_history << 4);
}
static void aptx_generate_dither(struct aptx_channel *channel)
{
    unsigned subband;
    int64_t m;
    int32_t d;

    aptx_update_codeword_history(channel);

    m = (int64_t)5184443 * (channel->codeword_history >> 7);
    d = (int32_t)((m * 4) + (m >> 22));
    for (subband = 0; subband < NB_SUBBANDS; subband++)
        channel->dither[subband] = (int32_t)((uint32_t)d << (23 - 5*subband));
    channel->dither_parity = (d >> 25) & 1;
}