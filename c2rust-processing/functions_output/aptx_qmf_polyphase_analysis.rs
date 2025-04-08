#![allow(
    dead_code,
    mutable_transmutes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    unused_mut
)]
pub type __uint8_t = libc::c_uchar;
pub type __int32_t = libc::c_int;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_filter_signal {
    pub buffer: [int32_t; 32],
    pub pos: uint8_t,
}
#[no_mangle]
pub unsafe extern "C" fn aptx_qmf_polyphase_analysis(
    mut signal: *mut aptx_filter_signal,
    mut coeffs: *const [int32_t; 16],
    mut shift: libc::c_uint,
    mut samples: *const int32_t,
    mut low_subband_output: *mut int32_t,
    mut high_subband_output: *mut int32_t,
) {
    let mut subbands: [int32_t; 2] = [0; 2];
    let mut i: libc::c_uint = 0;
    i = 0 as libc::c_int as libc::c_uint;
    while i < 2 as libc::c_int as libc::c_uint {
        aptx_qmf_filter_signal_push(
            &mut *signal.offset(i as isize),
            *samples
                .offset(
                    ((2 as libc::c_int - 1 as libc::c_int) as libc::c_uint)
                        .wrapping_sub(i) as isize,
                ),
        );
        subbands[i
            as usize] = aptx_qmf_convolution(
            &mut *signal.offset(i as isize),
            (*coeffs.offset(i as isize)).as_ptr(),
            shift,
        );
        i = i.wrapping_add(1);
        i;
    }
    *low_subband_output = clip_intp2(
        subbands[0 as libc::c_int as usize] + subbands[1 as libc::c_int as usize],
        23 as libc::c_int,
    );
    *high_subband_output = clip_intp2(
        subbands[0 as libc::c_int as usize] - subbands[1 as libc::c_int as usize],
        23 as libc::c_int,
    );
}
