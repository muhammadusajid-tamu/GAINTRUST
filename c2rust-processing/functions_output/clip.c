#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "openaptx.h"
#include "flex_extraction.h"
 inline int32_t clip(int32_t a, int32_t amin, int32_t amax)
{
    if      (a < amin) return amin;
    else if (a > amax) return amax;
    else               return a;
}