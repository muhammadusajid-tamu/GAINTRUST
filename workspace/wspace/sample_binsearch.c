#include <stdint.h>

#include <stdlib.h>

#include <string.h>






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