#[path = "../build-support/windows_resource.rs"]
mod windows_resource;

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    windows_resource::embed("rotki starling", "starling.exe");
}
