#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_prediction_filtering(struct aptx_prediction *prediction,
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