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
pub unsafe extern "C" fn aptx_qmf_filter_signal_push(
    mut signal: *mut aptx_filter_signal,
    mut sample: int32_t,
) {
    (*signal).buffer[(*signal).pos as usize] = sample;
    (*signal)
        .buffer[((*signal).pos as libc::c_int + 16 as libc::c_int) as usize] = sample;
    (*signal)
        .pos = ((*signal).pos as libc::c_int + 1 as libc::c_int
        & 16 as libc::c_int - 1 as libc::c_int) as uint8_t;
}
