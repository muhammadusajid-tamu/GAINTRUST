fn aptx_bin_search(value: isize, factor: isize, intervals: &mut [isize]) -> isize {
    let mut idx = 0;
    let len = intervals.len() as isize / 2;
    
    while idx < len {
        if (value as isize) * (interval as isize) <= ((value as isize) << 24) {
            idx += len;
        }
        else {
            break;
        }
    }

    idx
}