#![allow(
    dead_code,
    mutable_transmutes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    unused_mut
)]
pub type __int32_t = libc::c_int;
pub type __uint32_t = libc::c_uint;
pub type int32_t = __int32_t;
pub type uint32_t = __uint32_t;
#[no_mangle]
pub unsafe extern "C" fn clip_intp2(mut a: int32_t, mut p: libc::c_uint) -> int32_t {
    if (a as uint32_t).wrapping_add((1 as libc::c_int as uint32_t) << p)
        & !((2 as libc::c_int as uint32_t) << p)
            .wrapping_sub(1 as libc::c_int as libc::c_uint) != 0
    {
        return a >> 31 as libc::c_int ^ ((1 as libc::c_int) << p) - 1 as libc::c_int
    } else {
        return a
    };
}
