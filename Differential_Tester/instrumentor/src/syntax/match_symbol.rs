use std::{path::Path, process::Command};

pub fn symbol_list<P: AsRef<Path>>(path: P) -> Vec<String> {
    let output = Command::new("nm")
        .arg("-g")
        .arg(path.as_ref())
        .output()
        .expect("failed to execute nm, try disabling ground_truth option");

    let captured_stdout = String::from_utf8(output.stdout).expect("nm fails utf8");
    captured_stdout
        .lines()
        .filter_map(|line| {
            let splitted = line.split(' ').collect::<Vec<_>>();
            if splitted.len() == 3 && splitted[2].ends_with("__C") && !line.contains("cgoexp") {
                let symbol_name = splitted[2];
                Some(symbol_name.trim_start_matches('_').to_owned())
            } else {
                None
            }
        })
        .collect::<Vec<_>>()
}
