#include <stdint.h>

#include <stdlib.h>

#include <string.h>





struct aptx_tables {
    const int32_t *quantize_intervals;
    const int32_t *invert_quantize_dither_factors;
    const int32_t *quantize_dither_factors;
    const int16_t *quantize_factor_select_offset;
    int tables_size;
    int32_t factor_max;
    int prediction_order;
};
struct aptx_quantize {
    int32_t quantized_sample;
    int32_t quantized_sample_parity_change;
    int32_t error;
};
static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int64_t rshift64(int64_t value, unsigned shift) ;
static inline int32_t rshift64_clip24(int64_t value, unsigned shift) ;
static inline int32_t rshift32(int32_t value, unsigned shift) ;
static inline int32_t rshift32_clip24(int32_t value, unsigned shift) ;
static inline int32_t aptx_bin_search(int32_t value, int32_t factor,
                                      const int32_t *intervals, int nb_intervals)
;
static void aptx_quantize_difference(struct aptx_quantize *quantize,
                                     int32_t sample_difference,
                                     int32_t dither,
                                     int32_t quantization_factor,
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
static inline int32_t rshift32_clip24(int32_t value, unsigned shift) { return clip_intp2((int32_t)rshift32(value, shift), 23); }
static inline int32_t aptx_bin_search(int32_t value, int32_t factor,
                                      const int32_t *intervals, int nb_intervals)
{
    int32_t idx = 0;
    int i;

    for (i = nb_intervals >> 1; i > 0; i >>= 1)
        if ((int64_t)factor * (int64_t)intervals[idx + i] <= ((int64_t)value << 24))
            idx += i;

    return idx;
}
static void aptx_quantize_difference(struct aptx_quantize *quantize,
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