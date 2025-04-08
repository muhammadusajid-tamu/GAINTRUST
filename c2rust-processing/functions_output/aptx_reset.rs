#![allow(
    dead_code,
    mutable_transmutes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals,
    unused_assignments,
    unused_mut
)]
pub type size_t = libc::c_ulong;
pub type __uint8_t = libc::c_uchar;
pub type __int32_t = libc::c_int;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
#[derive(Copy, Clone)]
#[repr(C)]
pub struct aptx_context {
    pub decode_sync_packets: size_t,
    pub decode_dropped: size_t,
    pub channels: [aptx_channel; 2],
    pub hd: uint8_t,
    pub sync_idx: uint8_t,
    pub encode_remaining: uint8_t,
    pub decode_skip_leading: uint8_t,
    pub decode_sync_buffer_len: uint8_t,
    pub decode_sync_buffer: [libc::c_uchar; 6],
}
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
pub const NB_CHANNELS: channels = 2;
pub type channels = libc::c_uint;
pub const RIGHT: channels = 1;
pub const LEFT: channels = 0;
#[no_mangle]
pub unsafe extern "C" fn aptx_reset(mut ctx: *mut aptx_context) {
    let hd: uint8_t = (*ctx).hd;
    let mut i: libc::c_uint = 0;
    let mut chan: libc::c_uint = 0;
    let mut subband: libc::c_uint = 0;
    let mut channel: *mut aptx_channel = 0 as *mut aptx_channel;
    let mut prediction: *mut aptx_prediction = 0 as *mut aptx_prediction;
    i = 0 as libc::c_int as libc::c_uint;
    while (i as libc::c_ulong) < ::core::mem::size_of::<aptx_context>() as libc::c_ulong
    {
        *(ctx as *mut libc::c_uchar)
            .offset(i as isize) = 0 as libc::c_int as libc::c_uchar;
        i = i.wrapping_add(1);
        i;
    }
    (*ctx).hd = hd;
    (*ctx)
        .decode_skip_leading = ((90 as libc::c_int + 3 as libc::c_int)
        / 4 as libc::c_int) as uint8_t;
    (*ctx)
        .encode_remaining = ((90 as libc::c_int + 3 as libc::c_int) / 4 as libc::c_int)
        as uint8_t;
    chan = 0 as libc::c_int as libc::c_uint;
    while chan < NB_CHANNELS as libc::c_int as libc::c_uint {
        channel = &mut *((*ctx).channels).as_mut_ptr().offset(chan as isize)
            as *mut aptx_channel;
        subband = 0 as libc::c_int as libc::c_uint;
        while subband < 4 as libc::c_int as libc::c_uint {
            prediction = &mut *((*channel).prediction)
                .as_mut_ptr()
                .offset(subband as isize) as *mut aptx_prediction;
            (*prediction).prev_sign[0 as libc::c_int as usize] = 1 as libc::c_int;
            (*prediction).prev_sign[1 as libc::c_int as usize] = 1 as libc::c_int;
            subband = subband.wrapping_add(1);
            subband;
        }
        chan = chan.wrapping_add(1);
        chan;
    }
}
