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
pub type __int64_t = libc::c_long;
pub type int32_t = __int32_t;
pub type int64_t = __int64_t;
pub type uint8_t = __uint8_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_filter_signal {
    pub buffer: [int32_t; 32],
    pub pos: uint8_t,
}
#[no_mangle]
pub unsafe extern "C" fn aptx_qmf_convolution(
    mut signal: *const aptx_filter_signal,
    mut coeffs: *const int32_t,
    mut shift: libc::c_uint,
) -> int32_t {
    let mut sig: *const int32_t = &*((*signal).buffer)
        .as_ptr()
        .offset((*signal).pos as isize) as *const int32_t;
    let mut e: int64_t = 0 as libc::c_int as int64_t;
    let mut i: libc::c_uint = 0;
    i = 0 as libc::c_int as libc::c_uint;
    while i < 16 as libc::c_int as libc::c_uint {
        e += *sig.offset(i as isize) as int64_t * *coeffs.offset(i as isize) as int64_t;
        i = i.wrapping_add(1);
        i;
    }
    return rshift64_clip24(e, shift);
}
