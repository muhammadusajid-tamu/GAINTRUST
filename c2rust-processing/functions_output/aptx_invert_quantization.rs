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
pub struct aptx_invert_quantize {
    pub quantization_factor: int32_t,
    pub factor_select: int32_t,
    pub reconstructed_difference: int32_t,
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
static mut quantization_factors: [int16_t; 32] = [
    2048 as libc::c_int as int16_t,
    2093 as libc::c_int as int16_t,
    2139 as libc::c_int as int16_t,
    2186 as libc::c_int as int16_t,
    2233 as libc::c_int as int16_t,
    2282 as libc::c_int as int16_t,
    2332 as libc::c_int as int16_t,
    2383 as libc::c_int as int16_t,
    2435 as libc::c_int as int16_t,
    2489 as libc::c_int as int16_t,
    2543 as libc::c_int as int16_t,
    2599 as libc::c_int as int16_t,
    2656 as libc::c_int as int16_t,
    2714 as libc::c_int as int16_t,
    2774 as libc::c_int as int16_t,
    2834 as libc::c_int as int16_t,
    2896 as libc::c_int as int16_t,
    2960 as libc::c_int as int16_t,
    3025 as libc::c_int as int16_t,
    3091 as libc::c_int as int16_t,
    3158 as libc::c_int as int16_t,
    3228 as libc::c_int as int16_t,
    3298 as libc::c_int as int16_t,
    3371 as libc::c_int as int16_t,
    3444 as libc::c_int as int16_t,
    3520 as libc::c_int as int16_t,
    3597 as libc::c_int as int16_t,
    3676 as libc::c_int as int16_t,
    3756 as libc::c_int as int16_t,
    3838 as libc::c_int as int16_t,
    3922 as libc::c_int as int16_t,
    4008 as libc::c_int as int16_t,
];
#[no_mangle]
pub unsafe extern "C" fn aptx_invert_quantization(
    mut invert_quantize: *mut aptx_invert_quantize,
    mut quantized_sample: int32_t,
    mut dither: int32_t,
    mut tables: *const aptx_tables,
) {
    let mut qr: int32_t = 0;
    let mut idx: int32_t = 0;
    let mut shift: int32_t = 0;
    let mut factor_select: int32_t = 0;
    idx = (quantized_sample ^ -((quantized_sample < 0 as libc::c_int) as libc::c_int))
        + 1 as libc::c_int;
    qr = *((*tables).quantize_intervals).offset(idx as isize) / 2 as libc::c_int;
    if quantized_sample < 0 as libc::c_int {
        qr = -qr;
    }
    qr = rshift64_clip24(
        qr as int64_t * ((1 as libc::c_int as int64_t) << 32 as libc::c_int)
            + dither as int64_t
                * *((*tables).invert_quantize_dither_factors).offset(idx as isize)
                    as int64_t,
        32 as libc::c_int,
    );
    (*invert_quantize)
        .reconstructed_difference = ((*invert_quantize).quantization_factor as int64_t
        * qr as int64_t >> 19 as libc::c_int) as int32_t;
    factor_select = 32620 as libc::c_int * (*invert_quantize).factor_select;
    factor_select = rshift32(
        factor_select
            + *((*tables).quantize_factor_select_offset).offset(idx as isize)
                as libc::c_int * ((1 as libc::c_int) << 15 as libc::c_int),
        15 as libc::c_int,
    );
    (*invert_quantize)
        .factor_select = clip(factor_select, 0 as libc::c_int, (*tables).factor_max);
    idx = ((*invert_quantize).factor_select & 0xff as libc::c_int) >> 3 as libc::c_int;
    shift = (*tables).factor_max - (*invert_quantize).factor_select >> 8 as libc::c_int;
    (*invert_quantize)
        .quantization_factor = (quantization_factors[idx as usize] as libc::c_int)
        << 11 as libc::c_int >> shift;
}
