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
pub type int32_t = __int32_t;
#[no_mangle]
pub unsafe extern "C" fn clip(
    mut a: int32_t,
    mut amin: int32_t,
    mut amax: int32_t,
) -> int32_t {
    if a < amin { return amin } else if a > amax { return amax } else { return a };
}
