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
    fn aptx_encode_samples(
        ctx: *mut aptx_context,
        samples: *mut [int32_t; 4],
        output: *mut uint8_t,
    );
}
pub type size_t = libc::c_ulong;
pub type __int8_t = libc::c_schar;
pub type __uint8_t = libc::c_uchar;
pub type __int32_t = libc::c_int;
pub type __uint32_t = libc::c_uint;
pub type int8_t = __int8_t;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
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
pub const NB_CHANNELS: channels = 2;
pub type channels = libc::c_uint;
pub const RIGHT: channels = 1;
pub const LEFT: channels = 0;
#[no_mangle]
pub unsafe extern "C" fn aptx_encode(
    mut ctx: *mut aptx_context,
    mut input: *const libc::c_uchar,
    mut input_size: size_t,
    mut output: *mut libc::c_uchar,
    mut output_size: size_t,
    mut written: *mut size_t,
) -> size_t {
    let sample_size: size_t = (if (*ctx).hd as libc::c_int != 0 {
        6 as libc::c_int
    } else {
        4 as libc::c_int
    }) as size_t;
    let mut samples: [[int32_t; 4]; 2] = [[0; 4]; 2];
    let mut sample: libc::c_uint = 0;
    let mut channel: libc::c_uint = 0;
    let mut ipos: size_t = 0;
    let mut opos: size_t = 0;
    ipos = 0 as libc::c_int as size_t;
    opos = 0 as libc::c_int as size_t;
    while ipos
        .wrapping_add(
            (3 as libc::c_int * NB_CHANNELS as libc::c_int * 4 as libc::c_int)
                as libc::c_ulong,
        ) <= input_size && opos.wrapping_add(sample_size) <= output_size
    {
        sample = 0 as libc::c_int as libc::c_uint;
        while sample < 4 as libc::c_int as libc::c_uint {
            channel = 0 as libc::c_int as libc::c_uint;
            while channel < NB_CHANNELS as libc::c_int as libc::c_uint {
                samples[channel
                    as usize][sample
                    as usize] = ((*input
                    .offset(
                        ipos.wrapping_add(0 as libc::c_int as libc::c_ulong) as isize,
                    ) as uint32_t) << 0 as libc::c_int
                    | (*input
                        .offset(
                            ipos.wrapping_add(1 as libc::c_int as libc::c_ulong) as isize,
                        ) as uint32_t) << 8 as libc::c_int
                    | (*input
                        .offset(
                            ipos.wrapping_add(2 as libc::c_int as libc::c_ulong) as isize,
                        ) as int8_t as uint32_t) << 16 as libc::c_int) as int32_t;
                channel = channel.wrapping_add(1);
                channel;
                ipos = (ipos as libc::c_ulong)
                    .wrapping_add(3 as libc::c_int as libc::c_ulong) as size_t as size_t;
            }
            sample = sample.wrapping_add(1);
            sample;
        }
        aptx_encode_samples(ctx, samples.as_mut_ptr(), output.offset(opos as isize));
        opos = (opos as libc::c_ulong).wrapping_add(sample_size) as size_t as size_t;
    }
    *written = opos;
    return ipos;
}
