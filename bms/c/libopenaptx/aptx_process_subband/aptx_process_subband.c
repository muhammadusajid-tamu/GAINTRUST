#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define DIFFSIGN(x,y) (((x)>(y)) - ((x)<(y)))



static const int16_t quantization_factors[32] = {
    2048, 2093, 2139, 2186, 2233, 2282, 2332, 2383,
    2435, 2489, 2543, 2599, 2656, 2714, 2774, 2834,
    2896, 2960, 3025, 3091, 3158, 3228, 3298, 3371,
    3444, 3520, 3597, 3676, 3756, 3838, 3922, 4008,
};
struct aptx_tables {
    const int32_t *quantize_intervals;
    const int32_t *invert_quantize_dither_factors;
    const int32_t *quantize_dither_factors;
    const int16_t *quantize_factor_select_offset;
    int tables_size;
    int32_t factor_max;
    int prediction_order;
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
static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int64_t rshift64(int64_t value, unsigned shift) ;
static inline int32_t rshift64_clip24(int64_t value, unsigned shift) ;
static inline int32_t rshift32(int32_t value, unsigned shift) ;
static int32_t *aptx_reconstructed_differences_update(struct aptx_prediction *prediction,
                                                      int32_t reconstructed_difference,
                                                      int order)
;
static inline int32_t clip(int32_t a, int32_t amin, int32_t amax)
;
static void aptx_prediction_filtering(struct aptx_prediction *prediction,
                                      int32_t reconstructed_difference,
                                      int order)
;
static void aptx_invert_quantization(struct aptx_invert_quantize *invert_quantize,
                                     int32_t quantized_sample, int32_t dither,
                                     const struct aptx_tables *tables)
;
static void aptx_process_subband(struct aptx_invert_quantize *invert_quantize,
                                 struct aptx_prediction *prediction,
                                 int32_t quantized_sample, int32_t dither,
                                 const struct aptx_tables *tables)
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
static inline int32_t rshift32(int32_t value, unsigned shift) { const int32_t rounding = (int32_t)1 << (shift - 1); const int32_t mask = ((int32_t)1 << (shift + 1)) - 1; return ((value + rounding) >> shift) - ((value & mask) == rounding); }
static int32_t *aptx_reconstructed_differences_update(struct aptx_prediction *prediction,
                                                      int32_t reconstructed_difference,
                                                      int order)
{
    int32_t *rd1 = prediction->reconstructed_differences, *rd2 = rd1 + order;
    int p = prediction->pos;

    rd1[p] = rd2[p];
    prediction->pos = p = (p + 1) % order;
    rd2[p] = reconstructed_difference;
    return &rd2[p];
}
static inline int32_t clip(int32_t a, int32_t amin, int32_t amax)
{
    if      (a < amin) return amin;
    else if (a > amax) return amax;
    else               return a;
}
static void aptx_prediction_filtering(struct aptx_prediction *prediction,
                                      int32_t reconstructed_difference,
                                      int order)
{
    int32_t reconstructed_sample, predictor, srd0, srd;
    int32_t *reconstructed_differences;
    int64_t predicted_difference = 0;
    int i;

    reconstructed_sample = clip_intp2(reconstructed_difference + prediction->predicted_sample, 23);
    predictor = clip_intp2((int32_t)(((int64_t)prediction->s_weight[0] * (int64_t)prediction->previous_reconstructed_sample
                                    + (int64_t)prediction->s_weight[1] * (int64_t)reconstructed_sample) >> 22), 23);
    prediction->previous_reconstructed_sample = reconstructed_sample;

    reconstructed_differences = aptx_reconstructed_differences_update(prediction, reconstructed_difference, order);
    srd0 = (int32_t)DIFFSIGN(reconstructed_difference, 0) * ((int32_t)1 << 23);
    for (i = 0; i < order; i++) {
        srd = (reconstructed_differences[-i-1] >> 31) | 1;
        prediction->d_weight[i] -= rshift32(prediction->d_weight[i] - srd*srd0, 8);
        predicted_difference += (int64_t)reconstructed_differences[-i] * (int64_t)prediction->d_weight[i];
    }

    prediction->predicted_difference = clip_intp2((int32_t)(predicted_difference >> 22), 23);
    prediction->predicted_sample = clip_intp2(predictor + prediction->predicted_difference, 23);
}
static void aptx_invert_quantization(struct aptx_invert_quantize *invert_quantize,
                                     int32_t quantized_sample, int32_t dither,
                                     const struct aptx_tables *tables)
{
    int32_t qr, idx, shift, factor_select;

    idx = (quantized_sample ^ -(quantized_sample < 0)) + 1;
    qr = tables->quantize_intervals[idx] / 2;
    if (quantized_sample < 0)
        qr = -qr;

    qr = rshift64_clip24(((int64_t)qr * ((int64_t)1<<32)) + (int64_t)dither * (int64_t)tables->invert_quantize_dither_factors[idx], 32);
    invert_quantize->reconstructed_difference = (int32_t)(((int64_t)invert_quantize->quantization_factor * (int64_t)qr) >> 19);

    /* update factor_select */
    factor_select = 32620 * invert_quantize->factor_select;
    factor_select = rshift32(factor_select + (tables->quantize_factor_select_offset[idx] * (1 << 15)), 15);
    invert_quantize->factor_select = clip(factor_select, 0, tables->factor_max);

    /* update quantization factor */
    idx = (invert_quantize->factor_select & 0xFF) >> 3;
    shift = (tables->factor_max - invert_quantize->factor_select) >> 8;
    invert_quantize->quantization_factor = (quantization_factors[idx] << 11) >> shift;
}
static void aptx_process_subband(struct aptx_invert_quantize *invert_quantize,
                                 struct aptx_prediction *prediction,
                                 int32_t quantized_sample, int32_t dither,
                                 const struct aptx_tables *tables)
{
    int32_t sign, same_sign[2], weight[2], sw1, range;

    aptx_invert_quantization(invert_quantize, quantized_sample, dither, tables);

    sign = DIFFSIGN(invert_quantize->reconstructed_difference,
                    -prediction->predicted_difference);
    same_sign[0] = sign * prediction->prev_sign[0];
    same_sign[1] = sign * prediction->prev_sign[1];
    prediction->prev_sign[0] = prediction->prev_sign[1];
    prediction->prev_sign[1] = sign | 1;

    range = 0x100000;
    sw1 = rshift32(-same_sign[1] * prediction->s_weight[1], 1);
    sw1 = (clip(sw1, -range, range) & ~0xF) * 16;

    range = 0x300000;
    weight[0] = 254 * prediction->s_weight[0] + 0x800000*same_sign[0] + sw1;
    prediction->s_weight[0] = clip(rshift32(weight[0], 8), -range, range);

    range = 0x3C0000 - prediction->s_weight[0];
    weight[1] = 255 * prediction->s_weight[1] + 0xC00000*same_sign[1];
    prediction->s_weight[1] = clip(rshift32(weight[1], 8), -range, range);

    aptx_prediction_filtering(prediction,
                              invert_quantize->reconstructed_difference,
                              tables->prediction_order);
}