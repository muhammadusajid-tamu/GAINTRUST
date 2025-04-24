#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define DIFFSIGN(x,y) (((x)>(y)) - ((x)<(y)))




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
static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int32_t rshift32(int32_t value, unsigned shift) ;
static int32_t *aptx_reconstructed_differences_update(struct aptx_prediction *prediction,
                                                      int32_t reconstructed_difference,
                                                      int order)
;
static void aptx_prediction_filtering(struct aptx_prediction *prediction,
                                      int32_t reconstructed_difference,
                                      int order)
;
static inline int32_t clip_intp2(int32_t a, unsigned p)
{
    if (((uint32_t)a + ((uint32_t)1 << p)) & ~(((uint32_t)2 << p) - 1))
        return (a >> 31) ^ ((1 << p) - 1);
    else
        return a;
}
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