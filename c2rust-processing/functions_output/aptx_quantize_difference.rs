#![allow(
    dead_code,
    mutable_transmutes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    unused_mut
)]
pub type __int16_t = libc::c_short;
pub type __int32_t = libc::c_int;
pub type __int64_t = libc::c_long;
pub type int16_t = __int16_t;
pub type int32_t = __int32_t;
pub type int64_t = __int64_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_quantize {
    pub quantized_sample: int32_t,
    pub quantized_sample_parity_change: int32_t,
    pub error: int32_t,
}
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_tables {
    pub quantize_intervals: *const int32_t,
    pub invert_quantize_dither_factors: *const int32_t,
    pub quantize_dither_factors: *const int32_t,
    pub quantize_factor_select_offset: *const int16_t,
    pub tables_size: libc::c_int,
    pub factor_max: int32_t,
    pub prediction_order: libc::c_int,
}
#[no_mangle]
pub unsafe extern "C" fn aptx_quantize_difference(
    mut quantize: *mut aptx_quantize,
    mut sample_difference: int32_t,
    mut dither: int32_t,
    mut quantization_factor: int32_t,
    mut tables: *const aptx_tables,
) {
    let mut intervals: *const int32_t = (*tables).quantize_intervals;
    let mut quantized_sample: int32_t = 0;
    let mut dithered_sample: int32_t = 0;
    let mut parity_change: int32_t = 0;
    let mut d: int32_t = 0;
    let mut mean: int32_t = 0;
    let mut interval: int32_t = 0;
    let mut inv: int32_t = 0;
    let mut sample_difference_abs: int32_t = 0;
    let mut error: int64_t = 0;
    sample_difference_abs = sample_difference;
    if sample_difference_abs < 0 as libc::c_int {
        sample_difference_abs = -sample_difference_abs;
    }
    if sample_difference_abs
        > ((1 as libc::c_int) << 23 as libc::c_int) - 1 as libc::c_int
    {
        sample_difference_abs = ((1 as libc::c_int) << 23 as libc::c_int)
            - 1 as libc::c_int;
    }
    quantized_sample = aptx_bin_search(
        sample_difference_abs >> 4 as libc::c_int,
        quantization_factor,
        intervals,
        (*tables).tables_size,
    );
    d = rshift32_clip24(
        (dither as int64_t * dither as int64_t >> 32 as libc::c_int) as int32_t,
        7 as libc::c_int,
    ) - ((1 as libc::c_int) << 23 as libc::c_int);
    d = rshift64(
        d as int64_t
            * *((*tables).quantize_dither_factors).offset(quantized_sample as isize)
                as int64_t,
        23 as libc::c_int,
    );
    intervals = intervals.offset(quantized_sample as isize);
    mean = (*intervals.offset(1 as libc::c_int as isize)
        + *intervals.offset(0 as libc::c_int as isize)) / 2 as libc::c_int;
    interval = (*intervals.offset(1 as libc::c_int as isize)
        - *intervals.offset(0 as libc::c_int as isize))
        * (-((sample_difference < 0 as libc::c_int) as libc::c_int) | 1 as libc::c_int);
    dithered_sample = rshift64_clip24(
        dither as int64_t * interval as int64_t
            + ((clip_intp2(mean + d, 23 as libc::c_int) as int64_t)
                << 32 as libc::c_int),
        32 as libc::c_int,
    );
    error = ((sample_difference_abs as int64_t) << 20 as libc::c_int)
        - dithered_sample as int64_t * quantization_factor as int64_t;
    (*quantize).error = rshift64(error, 23 as libc::c_int);
    if (*quantize).error < 0 as libc::c_int {
        (*quantize).error = -(*quantize).error;
    }
    parity_change = quantized_sample;
    if error < 0 as libc::c_int as libc::c_long {
        quantized_sample -= 1;
        quantized_sample;
    } else {
        parity_change -= 1;
        parity_change;
    }
    inv = -((sample_difference < 0 as libc::c_int) as libc::c_int);
    (*quantize).quantized_sample = quantized_sample ^ inv;
    (*quantize).quantized_sample_parity_change = parity_change ^ inv;
}
