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
    fn aptx_qmf_tree_analysis(
        qmf: *mut aptx_QMF_analysis,
        samples: *const int32_t,
        subband_samples: *mut int32_t,
    );
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
#[no_mangle]
pub unsafe extern "C" fn aptx_encode_channel(
    mut channel: *mut aptx_channel,
    mut samples: *const int32_t,
    mut hd: libc::c_int,
) {
    let mut subband_samples: [int32_t; 4] = [0; 4];
    let mut diff: int32_t = 0;
    let mut subband: libc::c_uint = 0;
    aptx_qmf_tree_analysis(&mut (*channel).qmf, samples, subband_samples.as_mut_ptr());
    aptx_generate_dither(channel);
    subband = 0 as libc::c_int as libc::c_uint;
    while subband < 4 as libc::c_int as libc::c_uint {
        diff = clip_intp2(
            subband_samples[subband as usize]
                - (*channel).prediction[subband as usize].predicted_sample,
            23 as libc::c_int,
        );
        subband = subband.wrapping_add(1);
        subband;
    }
}
