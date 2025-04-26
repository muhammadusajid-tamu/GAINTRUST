#![allow(
    dead_code,
    mutable_transmutes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    unused_mut
)]
extern "C" {
    fn aptx_invert_quantization(
        invert_quantize: *mut aptx_invert_quantize,
        quantized_sample: int32_t,
        dither: int32_t,
        tables: *const aptx_tables,
    );
    fn aptx_prediction_filtering(
        prediction: *mut aptx_prediction,
        reconstructed_difference: int32_t,
        order: libc::c_int,
    );
}
pub type __int16_t = libc::c_short;
pub type __int32_t = libc::c_int;
pub type int16_t = __int16_t;
pub type int32_t = __int32_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_prediction {
    pub prev_sign: [int32_t; 2],
    pub s_weight: [int32_t; 2],
    pub d_weight: [int32_t; 24],
    pub pos: int32_t,
    pub reconstructed_differences: [int32_t; 48],
    pub previous_reconstructed_sample: int32_t,
    pub predicted_difference: int32_t,
    pub predicted_sample: int32_t,
}
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
#[no_mangle]
pub unsafe extern "C" fn aptx_process_subband(
    mut invert_quantize: *mut aptx_invert_quantize,
    mut prediction: *mut aptx_prediction,
    mut quantized_sample: int32_t,
    mut dither: int32_t,
    mut tables: *const aptx_tables,
) {
    let mut sign: int32_t = 0;
    let mut same_sign: [int32_t; 2] = [0; 2];
    let mut weight: [int32_t; 2] = [0; 2];
    let mut sw1: int32_t = 0;
    let mut range: int32_t = 0;
    aptx_invert_quantization(invert_quantize, quantized_sample, dither, tables);
    sign = ((*invert_quantize).reconstructed_difference
        > -(*prediction).predicted_difference) as libc::c_int
        - ((*invert_quantize).reconstructed_difference
            < -(*prediction).predicted_difference) as libc::c_int;
    same_sign[0 as libc::c_int
        as usize] = sign * (*prediction).prev_sign[0 as libc::c_int as usize];
    same_sign[1 as libc::c_int
        as usize] = sign * (*prediction).prev_sign[1 as libc::c_int as usize];
    (*prediction)
        .prev_sign[0 as libc::c_int
        as usize] = (*prediction).prev_sign[1 as libc::c_int as usize];
    (*prediction).prev_sign[1 as libc::c_int as usize] = sign | 1 as libc::c_int;
    range = 0x100000 as libc::c_int;
    sw1 = rshift32(
        -same_sign[1 as libc::c_int as usize]
            * (*prediction).s_weight[1 as libc::c_int as usize],
        1 as libc::c_int,
    );
    sw1 = (clip(sw1, -range, range) & !(0xf as libc::c_int)) * 16 as libc::c_int;
    range = 0x300000 as libc::c_int;
    weight[0 as libc::c_int
        as usize] = 254 as libc::c_int
        * (*prediction).s_weight[0 as libc::c_int as usize]
        + 0x800000 as libc::c_int * same_sign[0 as libc::c_int as usize] + sw1;
    (*prediction)
        .s_weight[0 as libc::c_int
        as usize] = clip(
        rshift32(weight[0 as libc::c_int as usize], 8 as libc::c_int),
        -range,
        range,
    );
    range = 0x3c0000 as libc::c_int - (*prediction).s_weight[0 as libc::c_int as usize];
    weight[1 as libc::c_int
        as usize] = 255 as libc::c_int
        * (*prediction).s_weight[1 as libc::c_int as usize]
        + 0xc00000 as libc::c_int * same_sign[1 as libc::c_int as usize];
    (*prediction)
        .s_weight[1 as libc::c_int
        as usize] = clip(
        rshift32(weight[1 as libc::c_int as usize], 8 as libc::c_int),
        -range,
        range,
    );
    aptx_prediction_filtering(
        prediction,
        (*invert_quantize).reconstructed_difference,
        (*tables).prediction_order,
    );
}
