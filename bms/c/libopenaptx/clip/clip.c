#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int32_t clip(int32_t a, int32_t amin, int32_t amax)
;
static inline int32_t clip(int32_t a, int32_t amin, int32_t amax)
{
    if      (a < amin) return amin;
    else if (a > amax) return amax;
    else               return a;
}