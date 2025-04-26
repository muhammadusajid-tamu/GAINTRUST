#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"

 void aptx_quantize_difference(struct aptx_quantize *quantize,
                                     int32_t sample_difference,
                                     int32_t dither,
                                     int32_t quantization_factor,
                                     const struct aptx_tables *tables)
{
    const int32_t *intervals = tables->quantize_intervals;
    int32_t quantized_sample, dithered_sample, parity_change;
    int32_t d, mean, interval, inv, sample_difference_abs;
    int64_t error;

    sample_difference_abs = sample_difference;
    if (sample_difference_abs < 0)
        sample_difference_abs = -sample_difference_abs;
    if (sample_difference_abs > ((int32_t)1 << 23) - 1)
        sample_difference_abs = ((int32_t)1 << 23) - 1;

    quantized_sample = aptx_bin_search(sample_difference_abs >> 4,
                                       quantization_factor,
                                       intervals, tables->tables_size);

    d = rshift32_clip24((int32_t)(((int64_t)dither * (int64_t)dither) >> 32), 7) - ((int32_t)1 << 23);
    d = (int32_t)rshift64((int64_t)d * (int64_t)tables->quantize_dither_factors[quantized_sample], 23);

    intervals += quantized_sample;
    mean = (intervals[1] + intervals[0]) / 2;
    interval = (intervals[1] - intervals[0]) * (-(sample_difference < 0) | 1);

    dithered_sample = rshift64_clip24((int64_t)dither * (int64_t)interval + ((int64_t)clip_intp2(mean + d, 23) << 32), 32);
    error = ((int64_t)sample_difference_abs << 20) - (int64_t)dithered_sample * (int64_t)quantization_factor;
    quantize->error = (int32_t)rshift64(error, 23);
    if (quantize->error < 0)
        quantize->error = -quantize->error;

    parity_change = quantized_sample;
    if (error < 0)
        quantized_sample--;
    else
        parity_change--;

    inv = -(sample_difference < 0);
    quantize->quantized_sample               = quantized_sample ^ inv;
    quantize->quantized_sample_parity_change = parity_change    ^ inv;
}