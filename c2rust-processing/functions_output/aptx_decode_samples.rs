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
    fn aptx_generate_dither(channel: *mut aptx_channel);
    fn aptx_decode_channel(channel: *mut aptx_channel, samples: *mut int32_t);
    fn aptx_invert_quantize_and_prediction(channel: *mut aptx_channel, hd: libc::c_int);
    fn aptx_check_parity(
        channels: *const aptx_channel,
        sync_idx: *mut uint8_t,
    ) -> libc::c_int;
    fn aptx_unpack_codeword(channel: *mut aptx_channel, codeword: uint16_t);
    fn aptxhd_unpack_codeword(channel: *mut aptx_channel, codeword: uint32_t);
}
pub type size_t = libc::c_ulong;
pub type __uint8_t = libc::c_uchar;
pub type __uint16_t = libc::c_ushort;
pub type __int32_t = libc::c_int;
pub type __uint32_t = libc::c_uint;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
pub type uint16_t = __uint16_t;
pub type uint32_t = __uint32_t;
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
pub type channels = libc::c_uint;
pub const NB_CHANNELS: channels = 2;
pub const RIGHT: channels = 1;
pub const LEFT: channels = 0;
#[no_mangle]
pub unsafe extern "C" fn aptx_decode_samples(
    mut ctx: *mut aptx_context,
    mut input: *const uint8_t,
    mut samples: *mut [int32_t; 4],
) -> libc::c_int {
    let mut channel: libc::c_uint = 0;
    let mut ret: libc::c_int = 0;
    channel = 0 as libc::c_int as libc::c_uint;
    while channel < NB_CHANNELS as libc::c_int as libc::c_uint {
        aptx_generate_dither(
            &mut *((*ctx).channels).as_mut_ptr().offset(channel as isize),
        );
        if (*ctx).hd != 0 {
            aptxhd_unpack_codeword(
                &mut *((*ctx).channels).as_mut_ptr().offset(channel as isize),
                (*input
                    .offset(
                        (3 as libc::c_int as libc::c_uint)
                            .wrapping_mul(channel)
                            .wrapping_add(0 as libc::c_int as libc::c_uint) as isize,
                    ) as uint32_t) << 16 as libc::c_int
                    | (*input
                        .offset(
                            (3 as libc::c_int as libc::c_uint)
                                .wrapping_mul(channel)
                                .wrapping_add(1 as libc::c_int as libc::c_uint) as isize,
                        ) as uint32_t) << 8 as libc::c_int
                    | (*input
                        .offset(
                            (3 as libc::c_int as libc::c_uint)
                                .wrapping_mul(channel)
                                .wrapping_add(2 as libc::c_int as libc::c_uint) as isize,
                        ) as uint32_t) << 0 as libc::c_int,
            );
        } else {
            aptx_unpack_codeword(
                &mut *((*ctx).channels).as_mut_ptr().offset(channel as isize),
                ((*input
                    .offset(
                        (2 as libc::c_int as libc::c_uint)
                            .wrapping_mul(channel)
                            .wrapping_add(0 as libc::c_int as libc::c_uint) as isize,
                    ) as uint16_t as libc::c_int) << 8 as libc::c_int
                    | (*input
                        .offset(
                            (2 as libc::c_int as libc::c_uint)
                                .wrapping_mul(channel)
                                .wrapping_add(1 as libc::c_int as libc::c_uint) as isize,
                        ) as uint16_t as libc::c_int) << 0 as libc::c_int) as uint16_t,
            );
        }
        aptx_invert_quantize_and_prediction(
            &mut *((*ctx).channels).as_mut_ptr().offset(channel as isize),
            (*ctx).hd as libc::c_int,
        );
        channel = channel.wrapping_add(1);
        channel;
    }
    ret = aptx_check_parity(
        ((*ctx).channels).as_mut_ptr() as *const aptx_channel,
        &mut (*ctx).sync_idx,
    );
    channel = 0 as libc::c_int as libc::c_uint;
    while channel < NB_CHANNELS as libc::c_int as libc::c_uint {
        aptx_decode_channel(
            &mut *((*ctx).channels).as_mut_ptr().offset(channel as isize),
            (*samples.offset(channel as isize)).as_mut_ptr(),
        );
        channel = channel.wrapping_add(1);
        channel;
    }
    return ret;
}
