use std::fs;
use std::io::{self, Write};
use std::path::Path;
use std::thread;
use std::time::Duration;

/// One thermal sensor exposed by the kernel under /sys/class/thermal.
struct Sensor {
    /// Human-readable sensor name, e.g. "x86_pkg_temp".
    label: String,
    /// Temperature in degrees Celsius.
    celsius: f64,
}

/// Translate a firmware/ACPI sensor label into a human-readable name.
/// These short codes come straight from the laptop's firmware, so we
/// map the ones we recognise and fall back to the raw label otherwise.
fn friendly_name(label: &str) -> &str {
    match label {
        "x86_pkg_temp" => "CPU package",
        "TCPU" => "CPU",
        "TCPU_PCI" => "CPU (PCI)",
        "CPUV" => "CPU voltage regulator",
        "iwlwifi_1" => "Wi-Fi card",
        "BATT" => "Battery",
        "CHRG" => "Charger",
        "AMBF" => "Ambient (front)",
        "BSKN" => "Base (underside)",
        "TSKN" => "Keyboard deck",
        "INT3400 Thermal" => "DPTF manager (not a sensor)",
        other => other,
    }
}

/// Read a single sysfs file and return its trimmed contents.
fn read_trimmed(path: &Path) -> io::Result<String> {
    Ok(fs::read_to_string(path)?.trim().to_owned())
}

/// Collect every readable thermal zone under /sys/class/thermal.
fn read_sensors() -> io::Result<Vec<Sensor>> {
    let mut sensors = Vec::new();

    for entry in fs::read_dir("/sys/class/thermal")? {
        let dir = entry?.path();

        // We only care about thermal_zoneN directories.
        let is_zone = dir
            .file_name()
            .and_then(|n| n.to_str())
            .is_some_and(|n| n.starts_with("thermal_zone"));
        if !is_zone {
            continue;
        }

        // `type` is the sensor name, `temp` is millidegrees Celsius.
        let label = read_trimmed(&dir.join("type"))?;
        let millidegrees: i64 = match read_trimmed(&dir.join("temp")) {
            Ok(raw) => raw.parse().unwrap_or(0),
            Err(_) => continue, // some zones have no temp file
        };

        sensors.push(Sensor {
            label,
            celsius: millidegrees as f64 / 1000.0,
        });
    }

    sensors.sort_by(|a, b| friendly_name(&a.label).cmp(friendly_name(&b.label)));
    Ok(sensors)
}

fn main() {
    let mut stdout = io::stdout();

    // Hide the cursor and clear the screen once up front.
    print!("\x1b[?25l\x1b[2J");

    loop {
        // Move the cursor to the top-left instead of scrolling, so each
        // refresh overwrites the previous frame in place.
        print!("\x1b[H");

        match read_sensors() {
            Ok(sensors) => {
                println!("Temperatures (Ctrl-C to quit)\n");
                for s in &sensors {
                    // \x1b[K clears any leftover characters from a longer
                    // previous line before printing this one.
                    println!("{:<28} {:>6.1} °C\x1b[K", friendly_name(&s.label), s.celsius);
                }
            }
            Err(e) => eprintln!("failed to read thermal zones: {e}\x1b[K"),
        }

        // Flush so the frame appears immediately, then wait before refreshing.
        let _ = stdout.flush();
        thread::sleep(Duration::from_secs(1));
    }
}
