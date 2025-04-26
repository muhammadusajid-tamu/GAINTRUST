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
    fn aptx_reconstructed_differences_update(
        prediction: *mut aptx_prediction,
        reconstructed_difference: int32_t,
        order: libc::c_int,
    ) -> *mut int32_t;
}
pub type __int32_t = libc::c_int;
pub type __int64_t = libc::c_long;
pub type int32_t = __int32_t;
pub type int64_t = __int64_t;
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
#[no_mangle]
pub unsafe extern "C" fn aptx_prediction_filtering(
    mut prediction: *mut aptx_prediction,
    mut reconstructed_difference: int32_t,
    mut order: libc::c_int,
) {
    let mut reconstructed_sample: int32_t = 0;
    let mut predictor: int32_t = 0;
    let mut srd0: int32_t = 0;
    let mut srd: int32_t = 0;
    let mut reconstructed_differences: *mut int32_t = 0 as *mut int32_t;
    let mut predicted_difference: int64_t = 0 as libc::c_int as int64_t;
    let mut i: libc::c_int = 0;
    reconstructed_sample = clip_intp2(
        reconstructed_difference + (*prediction).predicted_sample,
        23 as libc::c_int,
    );
    predictor = clip_intp2(
        ((*prediction).s_weight[0 as libc::c_int as usize] as int64_t
            * (*prediction).previous_reconstructed_sample as int64_t
            + (*prediction).s_weight[1 as libc::c_int as usize] as int64_t
                * reconstructed_sample as int64_t >> 22 as libc::c_int) as int32_t,
        23 as libc::c_int,
    );
    (*prediction).previous_reconstructed_sample = reconstructed_sample;
    reconstructed_differences = aptx_reconstructed_differences_update(
        prediction,
        reconstructed_difference,
        order,
    );
    srd0 = ((reconstructed_difference > 0 as libc::c_int) as libc::c_int
        - (reconstructed_difference < 0 as libc::c_int) as libc::c_int)
        * ((1 as libc::c_int) << 23 as libc::c_int);
    i = 0 as libc::c_int;
    while i < order {
        srd = *reconstructed_differences.offset((-i - 1 as libc::c_int) as isize)
            >> 31 as libc::c_int | 1 as libc::c_int;
        (*prediction).d_weight[i as usize]
            -= rshift32(
                (*prediction).d_weight[i as usize] - srd * srd0,
                8 as libc::c_int,
            );
        predicted_difference
            += *reconstructed_differences.offset(-i as isize) as int64_t
                * (*prediction).d_weight[i as usize] as int64_t;
        i += 1;
        i;
    }
    (*prediction)
        .predicted_difference = clip_intp2(
        (predicted_difference >> 22 as libc::c_int) as int32_t,
        23 as libc::c_int,
    );
    (*prediction)
        .predicted_sample = clip_intp2(
        predictor + (*prediction).predicted_difference,
        23 as libc::c_int,
    );
}
