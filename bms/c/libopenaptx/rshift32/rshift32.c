#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int32_t rshift32(int32_t value, unsigned shift) ;
static inline int32_t rshift32(int32_t value, unsigned shift) { const int32_t rounding = (int32_t)1 << (shift - 1); const int32_t mask = ((int32_t)1 << (shift + 1)) - 1; return ((value + rounding) >> shift) - ((value & mask) == rounding); }