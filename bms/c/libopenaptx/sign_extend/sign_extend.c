#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int32_t sign_extend(int32_t val, unsigned bits)
;
static inline int32_t sign_extend(int32_t val, unsigned bits)
{
    const unsigned shift = 8 * sizeof(val) - bits;
    union { uint32_t u; int32_t s; } v;
    v.u = (uint32_t)val << shift;
    return v.s >> shift;
}