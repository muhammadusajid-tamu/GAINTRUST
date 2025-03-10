from analysis.config import feedback_strats, llms, projects, bm_data, data, lints
c2rust = {
'opl_emu_abs_sin_attenuation':280,
'opl_emu_attenuation_increment':89,
'opl_emu_attenuation_to_volume':268,
'opl_emu_bitfield':12,
'opl_emu_clamp':17,
'opl_emu_fm_channel_assign':79,
'opl_emu_fm_channel_init':77,
'opl_emu_fm_channel_is4op':68,
'opl_emu_fm_channel_keyonoff':111,
'opl_emu_fm_operator_choffs':56,
'opl_emu_fm_operator_clock_envelope':192,
'opl_emu_fm_operator_clock_keystate':93,
'opl_emu_fm_operator_envelope_attenuation':105,
'opl_emu_fm_operator_init':66,
'opl_emu_fm_operator_keyonoff':75,
'opl_emu_fm_operator_opoffs':56,
'opl_emu_fm_operator_phase':56,
'opl_emu_fm_operator_reset':58,
'opl_emu_fm_operator_set_choffs':57,
'opl_emu_fm_operator_start_attack':67,
'opl_emu_fm_operator_start_release':61,
'opl_emu_init':948,
'opl_emu_opl_clock_noise_and_lfo':12,
'opl_emu_opl_compute_phase_step':12,
'opl_emu_opl_key_scale_atten':38,
'opl_emu_registers_byte':40,
'opl_emu_registers_ch_algorithm':61,
'opl_emu_registers_channel_offset':14,
'opl_emu_registers_ch_block_freq':70,
'opl_emu_registers_ch_feedback':53,
'opl_emu_registers_ch_output_0':69,
'opl_emu_registers_ch_output_1':69,
'opl_emu_registers_ch_output_2':69,
'opl_emu_registers_ch_output_3':69,
'opl_emu_registers_ch_output_any':69,
'opl_emu_registers_clock_noise_and_lfo':129,
'opl_emu_registers_effective_rate':16,
'opl_emu_registers_fourop_enable':52,
'opl_emu_registers_init':431,
'opl_emu_registers_is_rhythm':61,
'opl_emu_registers_lfo_am_depth':52,
'opl_emu_registers_lfo_am_offset':24,
'opl_emu_registers_lfo_pm_depth':52,
'opl_emu_registers_newflag':52,
'opl_emu_registers_noise_state':23,
'opl_emu_registers_note_select':52,
'opl_emu_registers_op_attack_rate':53,
'opl_emu_registers_op_decay_rate':53,
'opl_emu_registers_op_eg_sustain':53,
'opl_emu_registers_operator_list':16,
'opl_emu_registers_operator_map':339,
'opl_emu_registers_operator_offset':22,
'opl_emu_registers_op_ksl':55,
'opl_emu_registers_op_ksr':53,
'opl_emu_registers_op_lfo_am_enable':53,
'opl_emu_registers_op_lfo_pm_enable':53,
'opl_emu_registers_op_multiple':53,
'opl_emu_registers_op_release_rate':53,
'opl_emu_registers_op_sustain_level':53,
'opl_emu_registers_op_total_level':53,
'opl_emu_registers_op_waveform':69,
'opl_emu_registers_reset':26,
'opl_emu_registers_reset_lfo':22,
'opl_emu_registers_rhythm_enable':52,
'opl_emu_registers_status_mask':52,
'opl_emu_registers_timer_a_value':53,
'opl_emu_registers_timer_b_value':52,
'opl_emu_registers_word':54,
'opl_emu_registers_write':88,
'opl_emu_set_reset_status':118,
'opl_emu_update_timer':143,
'opl_emu_write':247,
'opl_loadbank_ibk':289,
'opl_loadbank_op2':202,
'opl_midi_changeprog':122,
'opl_midi_noteon':1228,
'opl_write':322,
}

res = []
for bench, loc in c2rust.items():
    rows = data[(data["benchmark_name"] == bench) & (data["final_status"] == "Success")]
    if len(rows) > 0:
        res.append(loc / rows["translation_loc"].mean())
print(sum(res)/len(res))