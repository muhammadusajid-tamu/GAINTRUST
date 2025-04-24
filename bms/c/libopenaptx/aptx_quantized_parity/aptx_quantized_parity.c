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
static int32_t aptx_quantized_parity(const struct aptx_channel *channel)
;
static int32_t aptx_quantized_parity(const struct aptx_channel *channel)
{
    int32_t parity = channel->dither_parity;
    unsigned subband;

    for (subband = 0; subband < NB_SUBBANDS; subband++)
        parity ^= channel->quantize[subband].quantized_sample;

    return parity & 1;
}