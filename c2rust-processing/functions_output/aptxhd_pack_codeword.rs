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
    fn aptx_quantized_parity(channel: *const aptx_channel) -> int32_t;
}
pub type __uint8_t = libc::c_uchar;
pub type __int32_t = libc::c_int;
pub type __uint32_t = libc::c_uint;
pub type int32_t = __int32_t;
pub type uint8_t = __uint8_t;
pub type uint32_t = __uint32_t;
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
#[no_mangle]
pub unsafe extern "C" fn aptxhd_pack_codeword(
    mut channel: *const aptx_channel,
) -> uint32_t {
    let parity: int32_t = aptx_quantized_parity(channel);
    return (((*channel).quantize[3 as libc::c_int as usize].quantized_sample
        & 0x1e as libc::c_int | parity) << 19 as libc::c_int
        | ((*channel).quantize[2 as libc::c_int as usize].quantized_sample
            & 0xf as libc::c_int) << 15 as libc::c_int
        | ((*channel).quantize[1 as libc::c_int as usize].quantized_sample
            & 0x3f as libc::c_int) << 9 as libc::c_int
        | ((*channel).quantize[0 as libc::c_int as usize].quantized_sample
            & 0x1ff as libc::c_int) << 0 as libc::c_int) as uint32_t;
}
