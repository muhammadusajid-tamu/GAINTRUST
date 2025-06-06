#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int32_t rshift32(int32_t value, unsigned shift) ;
static inline int32_t rshift32_clip24(int32_t value, unsigned shift) ;
static inline int32_t clip_intp2(int32_t a, unsigned p)
{
    if (((uint32_t)a + ((uint32_t)1 << p)) & ~(((uint32_t)2 << p) - 1))
        return (a >> 31) ^ ((1 << p) - 1);
    else
        return a;
}
static inline int32_t rshift32(int32_t value, unsigned shift) { const int32_t rounding = (int32_t)1 << (shift - 1); const int32_t mask = ((int32_t)1 << (shift + 1)) - 1; return ((value + rounding) >> shift) - ((value & mask) == rounding); }
static inline int32_t rshift32_clip24(int32_t value, unsigned shift) { return clip_intp2((int32_t)rshift32(value, shift), 23); }