//! Windows version resource, icon and application manifest for the bundled
//! executables, shared by each binary's `build.rs` through `#[path]`.
//!
//! An unsigned executable with no publisher metadata scores worse with
//! antivirus machine-learning heuristics (Defender has flagged colibri as
//! `Trojan:Win32/Bearfoos.A!ml`). Windows also shows these fields in Explorer,
//! Task Manager and quarantine reports. Keep the strings in line with
//! `windows_version_info` in `rotkehlchen.spec`, and the checked fields in
//! line with `missing_windows_resources` in `package.py`.

/// Embeds the version resource, the rotki icon and a manifest when building
/// for Windows.
pub fn embed(file_description: &str, original_filename: &str) {
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() != Ok("windows") {
        return;
    }

    // winresource is a Windows-host build dependency only: rotki builds its
    // Windows binaries natively, never cross-compiled.
    #[cfg(windows)]
    {
        let manifest_dir = std::path::PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
        let workspace_root = manifest_dir
            .ancestors()
            .find(|dir| dir.join("Cargo.lock").is_file())
            .expect("the crate is inside the cargo workspace");
        let icon = workspace_root.join("frontend/app/public/assets/images/rotki.ico");
        println!("cargo:rerun-if-changed={}", icon.display());
        let version = build_version();
        let release = release_parts(&version);
        // A file rather than `set_manifest`, which pads every line with
        // spaces and so puts one before the XML declaration.
        let manifest_path =
            std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap()).join("app.manifest");
        std::fs::write(
            &manifest_path,
            manifest(file_description, original_filename, release),
        )
        .expect("failed to write the Windows manifest");
        let [major, minor, patch] = release.map(u64::from);
        let numeric_version = major << 48 | minor << 32 | patch << 16;

        let mut resource = winresource::WindowsResource::new();
        resource
            .set_language(0x0409) // en-US, as electron-builder sets for rotki.exe
            .set_icon(icon.to_str().expect("the icon path is valid UTF-8"))
            .set_manifest_file(manifest_path.to_str().expect("OUT_DIR is valid UTF-8"))
            .set("CompanyName", "Rotki Solutions GmbH")
            .set("ProductName", "rotki")
            .set("FileDescription", file_description)
            .set("InternalName", original_filename)
            .set("OriginalFilename", original_filename)
            .set("LegalCopyright", "Copyright © Rotki Solutions GmbH")
            .set("FileVersion", &version)
            .set("ProductVersion", &version)
            .set_version_info(winresource::VersionInfo::FILEVERSION, numeric_version)
            .set_version_info(winresource::VersionInfo::PRODUCTVERSION, numeric_version);
        resource
            .compile()
            .expect("failed to embed the Windows resource");
    }

    #[cfg(not(windows))]
    let _ = (file_description, original_filename);
}

/// The version the binary is built as: `ROTKI_VERSION`, which the packaging
/// script sets to the setuptools_scm version (`1.44.2.dev2+g88731bd66f` on a
/// nightly), or the crate version for a plain `cargo` build. The same choice
/// colibri and starling make for `--version`.
#[cfg(windows)]
fn build_version() -> String {
    println!("cargo:rerun-if-env-changed=ROTKI_VERSION");
    std::env::var("ROTKI_VERSION").unwrap_or_else(|_| std::env::var("CARGO_PKG_VERSION").unwrap())
}

/// The `major.minor.patch` release part of `version`, as `rotkehlchen.spec`
/// takes it: the numeric version fields have no room for a dev or local suffix.
#[cfg(windows)]
fn release_parts(version: &str) -> [u16; 3] {
    let parts: Vec<u16> = version
        .split(|c: char| !c.is_ascii_digit())
        .take(3)
        .map(|part| part.parse().ok())
        .collect::<Option<_>>()
        .unwrap_or_default();
    parts
        .try_into()
        .unwrap_or_else(|_| panic!("version {version} does not start with major.minor.patch"))
}

/// rustc embeds no manifest of its own. This one only declares what the
/// binary already does: runs as the invoking user, on Windows 10 and later.
#[cfg(windows)]
fn manifest(file_description: &str, original_filename: &str, release: [u16; 3]) -> String {
    let name = original_filename.trim_end_matches(".exe");
    let [major, minor, patch] = release;
    format!(
        r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity type="win32" name="Rotki.{name}" version="{major}.{minor}.{patch}.0" processorArchitecture="*"/>
  <description>{file_description}</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <!-- Windows 10 and 11 -->
      <supportedOS Id="{{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}}"/>
    </application>
  </compatibility>
</assembly>
"#
    )
}
