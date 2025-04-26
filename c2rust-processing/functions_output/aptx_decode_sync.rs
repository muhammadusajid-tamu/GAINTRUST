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
    fn aptx_decode(
        ctx: *mut aptx_context,
        input: *const libc::c_uchar,
        input_size: size_t,
        output: *mut libc::c_uchar,
        output_size: size_t,
        written: *mut size_t,
    ) -> size_t;
    fn aptx_reset_decode_sync(ctx: *mut aptx_context);
}
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
pub unsafe extern "C" fn aptx_decode_sync(
    mut ctx: *mut aptx_context,
    mut input: *const libc::c_uchar,
    mut input_size: size_t,
    mut output: *mut libc::c_uchar,
    mut output_size: size_t,
    mut written: *mut size_t,
    mut synced: *mut libc::c_int,
    mut dropped: *mut size_t,
) -> size_t {
    let sample_size: size_t = (if (*ctx).hd as libc::c_int != 0 {
        6 as libc::c_int
    } else {
        4 as libc::c_int
    }) as size_t;
    let mut input_size_step: size_t = 0;
    let mut processed_step: size_t = 0;
    let mut written_step: size_t = 0;
    let mut ipos: size_t = 0 as libc::c_int as size_t;
    let mut opos: size_t = 0 as libc::c_int as size_t;
    let mut i: size_t = 0;
    *synced = 0 as libc::c_int;
    *dropped = 0 as libc::c_int as size_t;
    if (*ctx).decode_sync_buffer_len as libc::c_int > 0 as libc::c_int
        && sample_size
            .wrapping_sub(1 as libc::c_int as libc::c_ulong)
            .wrapping_sub((*ctx).decode_sync_buffer_len as libc::c_ulong) <= input_size
    {
        while ((*ctx).decode_sync_buffer_len as libc::c_ulong)
            < sample_size.wrapping_sub(1 as libc::c_int as libc::c_ulong)
        {
            let fresh0 = ipos;
            ipos = ipos.wrapping_add(1);
            let fresh1 = (*ctx).decode_sync_buffer_len;
            (*ctx)
                .decode_sync_buffer_len = ((*ctx).decode_sync_buffer_len)
                .wrapping_add(1);
            (*ctx).decode_sync_buffer[fresh1 as usize] = *input.offset(fresh0 as isize);
        }
    }
    while (*ctx).decode_sync_buffer_len as libc::c_ulong
        == sample_size.wrapping_sub(1 as libc::c_int as libc::c_ulong)
        && ipos < sample_size && ipos < input_size
        && (opos
            .wrapping_add(
                (3 as libc::c_int * NB_CHANNELS as libc::c_int * 4 as libc::c_int)
                    as libc::c_ulong,
            ) <= output_size
            || (*ctx).decode_skip_leading as libc::c_int > 0 as libc::c_int
            || (*ctx).decode_dropped > 0 as libc::c_int as libc::c_ulong)
    {
        let fresh2 = ipos;
        ipos = ipos.wrapping_add(1);
        (*ctx)
            .decode_sync_buffer[sample_size
            .wrapping_sub(1 as libc::c_int as libc::c_ulong)
            as usize] = *input.offset(fresh2 as isize);
        processed_step = aptx_decode(
            ctx,
            ((*ctx).decode_sync_buffer).as_mut_ptr(),
            sample_size,
            output.offset(opos as isize),
            output_size.wrapping_sub(opos),
            &mut written_step,
        );
        opos = (opos as libc::c_ulong).wrapping_add(written_step) as size_t as size_t;
        if (*ctx).decode_dropped > 0 as libc::c_int as libc::c_ulong
            && processed_step == sample_size
        {
            (*ctx)
                .decode_dropped = ((*ctx).decode_dropped as libc::c_ulong)
                .wrapping_add(processed_step) as size_t as size_t;
            (*ctx).decode_sync_packets = ((*ctx).decode_sync_packets).wrapping_add(1);
            (*ctx).decode_sync_packets;
            if (*ctx).decode_sync_packets
                >= ((90 as libc::c_int + 3 as libc::c_int) / 4 as libc::c_int)
                    as libc::c_ulong
            {
                *dropped = (*dropped as libc::c_ulong)
                    .wrapping_add((*ctx).decode_dropped) as size_t as size_t;
                (*ctx).decode_dropped = 0 as libc::c_int as size_t;
                (*ctx).decode_sync_packets = 0 as libc::c_int as size_t;
            }
        }
        if processed_step < sample_size {
            aptx_reset_decode_sync(ctx);
            *synced = 0 as libc::c_int;
            (*ctx).decode_dropped = ((*ctx).decode_dropped).wrapping_add(1);
            (*ctx).decode_dropped;
            (*ctx).decode_sync_packets = 0 as libc::c_int as size_t;
            i = 0 as libc::c_int as size_t;
            while i < sample_size.wrapping_sub(1 as libc::c_int as libc::c_ulong) {
                (*ctx)
                    .decode_sync_buffer[i
                    as usize] = (*ctx)
                    .decode_sync_buffer[i.wrapping_add(1 as libc::c_int as libc::c_ulong)
                    as usize];
                i = i.wrapping_add(1);
                i;
            }
        } else {
            if (*ctx).decode_dropped == 0 as libc::c_int as libc::c_ulong {
                *synced = 1 as libc::c_int;
            }
            (*ctx).decode_sync_buffer_len = 0 as libc::c_int as uint8_t;
        }
    }
    if (*ctx).decode_sync_buffer_len as libc::c_ulong
        == sample_size.wrapping_sub(1 as libc::c_int as libc::c_ulong)
        && ipos == sample_size
    {
        ipos = 0 as libc::c_int as size_t;
        (*ctx).decode_sync_buffer_len = 0 as libc::c_int as uint8_t;
    }
    while ipos.wrapping_add(sample_size) <= input_size
        && (opos
            .wrapping_add(
                (3 as libc::c_int * NB_CHANNELS as libc::c_int * 4 as libc::c_int)
                    as libc::c_ulong,
            ) <= output_size
            || (*ctx).decode_skip_leading as libc::c_int > 0 as libc::c_int
            || (*ctx).decode_dropped > 0 as libc::c_int as libc::c_ulong)
    {
        input_size_step = output_size
            .wrapping_sub(opos)
            .wrapping_div(3 as libc::c_int as libc::c_ulong)
            .wrapping_mul(NB_CHANNELS as libc::c_int as libc::c_ulong)
            .wrapping_mul(4 as libc::c_int as libc::c_ulong)
            .wrapping_add((*ctx).decode_skip_leading as libc::c_ulong)
            .wrapping_mul(sample_size);
        if input_size_step
            > input_size
                .wrapping_sub(ipos)
                .wrapping_div(sample_size)
                .wrapping_mul(sample_size)
        {
            input_size_step = input_size
                .wrapping_sub(ipos)
                .wrapping_div(sample_size)
                .wrapping_mul(sample_size);
        }
        if input_size_step
            > (((90 as libc::c_int + 3 as libc::c_int) / 4 as libc::c_int)
                as libc::c_ulong)
                .wrapping_sub((*ctx).decode_sync_packets)
                .wrapping_mul(sample_size)
            && (*ctx).decode_dropped > 0 as libc::c_int as libc::c_ulong
        {
            input_size_step = (((90 as libc::c_int + 3 as libc::c_int)
                / 4 as libc::c_int) as libc::c_ulong)
                .wrapping_sub((*ctx).decode_sync_packets)
                .wrapping_mul(sample_size);
        }
        processed_step = aptx_decode(
            ctx,
            input.offset(ipos as isize),
            input_size_step,
            output.offset(opos as isize),
            output_size.wrapping_sub(opos),
            &mut written_step,
        );
        ipos = (ipos as libc::c_ulong).wrapping_add(processed_step) as size_t as size_t;
        opos = (opos as libc::c_ulong).wrapping_add(written_step) as size_t as size_t;
        if (*ctx).decode_dropped > 0 as libc::c_int as libc::c_ulong
            && processed_step.wrapping_div(sample_size)
                > 0 as libc::c_int as libc::c_ulong
        {
            (*ctx)
                .decode_dropped = ((*ctx).decode_dropped as libc::c_ulong)
                .wrapping_add(processed_step) as size_t as size_t;
            (*ctx)
                .decode_sync_packets = ((*ctx).decode_sync_packets as libc::c_ulong)
                .wrapping_add(processed_step.wrapping_div(sample_size)) as size_t
                as size_t;
            if (*ctx).decode_sync_packets
                >= ((90 as libc::c_int + 3 as libc::c_int) / 4 as libc::c_int)
                    as libc::c_ulong
            {
                *dropped = (*dropped as libc::c_ulong)
                    .wrapping_add((*ctx).decode_dropped) as size_t as size_t;
                (*ctx).decode_dropped = 0 as libc::c_int as size_t;
                (*ctx).decode_sync_packets = 0 as libc::c_int as size_t;
            }
        }
        if processed_step < input_size_step {
            aptx_reset_decode_sync(ctx);
            *synced = 0 as libc::c_int;
            ipos = ipos.wrapping_add(1);
            ipos;
            (*ctx).decode_dropped = ((*ctx).decode_dropped).wrapping_add(1);
            (*ctx).decode_dropped;
            (*ctx).decode_sync_packets = 0 as libc::c_int as size_t;
        } else if (*ctx).decode_dropped == 0 as libc::c_int as libc::c_ulong {
            *synced = 1 as libc::c_int;
        }
    }
    if ipos.wrapping_add(sample_size) > input_size {
        while ipos < input_size {
            let fresh3 = ipos;
            ipos = ipos.wrapping_add(1);
            let fresh4 = (*ctx).decode_sync_buffer_len;
            (*ctx)
                .decode_sync_buffer_len = ((*ctx).decode_sync_buffer_len)
                .wrapping_add(1);
            (*ctx).decode_sync_buffer[fresh4 as usize] = *input.offset(fresh3 as isize);
        }
    }
    *written = opos;
    return ipos;
}
