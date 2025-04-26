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
    fn aptx_check_parity(
        channels: *const aptx_channel,
        sync_idx: *mut uint8_t,
    ) -> libc::c_int;
}
pub type __uint8_t = libc::c_uchar;
pub type __int32_t = libc::c_int;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_channel {
    pub codeword_history: int32_t,
    pub dither_parity: int32_t,
    pub dither: [int32_t; 4],
    pub qmf: aptx_QMF_analysis,
    pub quantize: [aptx_quantize; 4],
    pub invert_quantize: [aptx_invert_quantize; 4],
    pub prediction: [aptx_prediction; 4],
}
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
pub struct aptx_quantize {
    pub quantized_sample: int32_t,
    pub quantized_sample_parity_change: int32_t,
    pub error: int32_t,
}
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_QMF_analysis {
    pub outer_filter_signal: [aptx_filter_signal; 2],
    pub inner_filter_signal: [[aptx_filter_signal; 2]; 2],
}
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_filter_signal {
    pub buffer: [int32_t; 32],
    pub pos: uint8_t,
}
pub type channels = libc::c_uint;
pub const NB_CHANNELS: channels = 2;
pub const RIGHT: channels = 1;
pub const LEFT: channels = 0;
#[no_mangle]
pub unsafe extern "C" fn aptx_insert_sync(
    mut channels: *mut aptx_channel,
    mut sync_idx: *mut uint8_t,
) {
    let mut i: libc::c_uint = 0;
    let mut c: *mut aptx_channel = 0 as *mut aptx_channel;
    let map: [libc::c_uint; 4] = [
        1 as libc::c_int as libc::c_uint,
        2 as libc::c_int as libc::c_uint,
        0 as libc::c_int as libc::c_uint,
        3 as libc::c_int as libc::c_uint,
    ];
    let mut min: *mut aptx_quantize = &mut *((*channels
        .offset((NB_CHANNELS as libc::c_int - 1 as libc::c_int) as isize))
        .quantize)
        .as_mut_ptr()
        .offset(*map.as_ptr().offset(0 as libc::c_int as isize) as isize)
        as *mut aptx_quantize;
    if aptx_check_parity(channels as *const aptx_channel, sync_idx) != 0 {
        c = &mut *channels
            .offset((NB_CHANNELS as libc::c_int - 1 as libc::c_int) as isize)
            as *mut aptx_channel;
        while c >= channels {
            i = 0 as libc::c_int as libc::c_uint;
            while i < 4 as libc::c_int as libc::c_uint {
                if (*c).quantize[map[i as usize] as usize].error < (*min).error {
                    min = &mut *((*c).quantize)
                        .as_mut_ptr()
                        .offset(*map.as_ptr().offset(i as isize) as isize)
                        as *mut aptx_quantize;
                }
                i = i.wrapping_add(1);
                i;
            }
            c = c.offset(-1);
            c;
        }
        (*min).quantized_sample = (*min).quantized_sample_parity_change;
    }
}
