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
#[derive(Copy, Clone)]
#[repr(C)]
pub union C2RustUnnamed {
    pub u: uint32_t,
    pub s: int32_t,
}
#[no_mangle]
pub unsafe extern "C" fn sign_extend(
    mut val: int32_t,
    mut bits: libc::c_uint,
) -> int32_t {
    let shift: libc::c_uint = (8 as libc::c_int as libc::c_ulong)
        .wrapping_mul(::core::mem::size_of::<int32_t>() as libc::c_ulong)
        .wrapping_sub(bits as libc::c_ulong) as libc::c_uint;
    let mut v: C2RustUnnamed = C2RustUnnamed { u: 0 };
    v.u = (val as uint32_t) << shift;
    return v.s >> shift;
}
