#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define LATENCY_SAMPLES 90

#define NB_FILTERS 2

#define NB_SUBBANDS 4

#define FILTER_TAPS 16

enum channels {
    LEFT,
    RIGHT,
    NB_CHANNELS
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
struct aptx_context {
    size_t decode_sync_packets;
    size_t decode_dropped;
    struct aptx_channel channels[NB_CHANNELS];
    uint8_t hd;
    uint8_t sync_idx;
    uint8_t encode_remaining;
    uint8_t decode_skip_leading;
    uint8_t decode_sync_buffer_len;
    unsigned char decode_sync_buffer[6];
};
void aptx_reset(struct aptx_context *ctx)
;
static void aptx_reset_decode_sync(struct aptx_context *ctx)
;
void aptx_reset(struct aptx_context *ctx)
{
    const uint8_t hd = ctx->hd;
    unsigned i, chan, subband;
    struct aptx_channel *channel;
    struct aptx_prediction *prediction;

    for (i = 0; i < sizeof(*ctx); i++)
        ((unsigned char *)ctx)[i] = 0;

    ctx->hd = hd;
    ctx->decode_skip_leading = (LATENCY_SAMPLES+3)/4;
    ctx->encode_remaining = (LATENCY_SAMPLES+3)/4;

    for (chan = 0; chan < NB_CHANNELS; chan++) {
        channel = &ctx->channels[chan];
        for (subband = 0; subband < NB_SUBBANDS; subband++) {
            prediction = &channel->prediction[subband];
            prediction->prev_sign[0] = 1;
            prediction->prev_sign[1] = 1;
        }
    }
}
static void aptx_reset_decode_sync(struct aptx_context *ctx)
{
    const size_t decode_dropped = ctx->decode_dropped;
    const size_t decode_sync_packets = ctx->decode_sync_packets;
    const uint8_t decode_sync_buffer_len = ctx->decode_sync_buffer_len;
    unsigned char decode_sync_buffer[6];
    unsigned i;

    for (i = 0; i < 6; i++)
        decode_sync_buffer[i] = ctx->decode_sync_buffer[i];

    aptx_reset(ctx);

    for (i = 0; i < 6; i++)
        ctx->decode_sync_buffer[i] = decode_sync_buffer[i];

    ctx->decode_sync_buffer_len = decode_sync_buffer_len;
    ctx->decode_sync_packets = decode_sync_packets;
    ctx->decode_dropped = decode_dropped;
}