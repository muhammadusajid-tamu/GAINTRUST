#include <stdint.h>

#include <stdlib.h>

#include <string.h>

#define FILTER_TAPS 16




struct aptx_filter_signal {
    int32_t buffer[2*FILTER_TAPS];
    uint8_t pos;
};
static inline void aptx_qmf_filter_signal_push(struct aptx_filter_signal *signal,
                                               int32_t sample)
;
static inline void aptx_qmf_filter_signal_push(struct aptx_filter_signal *signal,
                                               int32_t sample)
{
    signal->buffer[signal->pos            ] = sample;
    signal->buffer[signal->pos+FILTER_TAPS] = sample;
    signal->pos = (signal->pos + 1) & (FILTER_TAPS - 1);
}