#include <stdint.h>

#include <stdlib.h>

#include <string.h>






static inline int32_t clip_intp2(int32_t a, unsigned p)
;
static inline int32_t clip_intp2(int32_t a, unsigned p)
{
    if (((uint32_t)a + ((uint32_t)1 << p)) & ~(((uint32_t)2 << p) - 1))
        return (a >> 31) ^ ((1 << p) - 1);
    else
        return a;
}