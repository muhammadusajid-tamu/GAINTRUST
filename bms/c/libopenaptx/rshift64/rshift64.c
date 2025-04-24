#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int64_t rshift64(int64_t value, unsigned shift) ;
static inline int64_t rshift64(int64_t value, unsigned shift) { const int64_t rounding = (int64_t)1 << (shift - 1); const int64_t mask = ((int64_t)1 << (shift + 1)) - 1; return ((value + rounding) >> shift) - ((value & mask) == rounding); }