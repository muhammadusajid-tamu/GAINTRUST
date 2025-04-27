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
pub type __int64_t = libc::c_long;
pub type int32_t = __int32_t;
pub type int64_t = __int64_t;
#[no_mangle]
pub unsafe extern "C" fn aptx_bin_search(
    mut value: int32_t,
    mut factor: int32_t,
    mut intervals: *const int32_t,
    mut nb_intervals: libc::c_int,
) -> int32_t {
    let mut idx: int32_t = 0 as libc::c_int;
    let mut i: libc::c_int = 0;
    i = nb_intervals >> 1 as libc::c_int;
    while i > 0 as libc::c_int {
        if factor as int64_t * *intervals.offset((idx + i) as isize) as int64_t
            <= (value as int64_t) << 24 as libc::c_int
        {
            idx += i;
        }
        i >>= 1 as libc::c_int;
    }
    return idx;
}
