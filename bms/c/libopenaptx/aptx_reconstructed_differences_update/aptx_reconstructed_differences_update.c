#include <stdint.h>

#include <stdlib.h>

#include <string.h>





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
static int32_t *aptx_reconstructed_differences_update(struct aptx_prediction *prediction,
                                                      int32_t reconstructed_difference,
                                                      int order)
;
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