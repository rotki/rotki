# Appveyor setup borrowed from excellent https://github.com/micbou/vim-for-windows

Function GetMajorMinorVersion($version) {
    $version_array = $version.Split('.')
    $version_array[0] + '.' + $version_array[1]
}

$msvc = $env:appveyor_build_worker_image.Substring($env:appveyor_build_worker_image.Length-4)
If ($msvc -eq 2013) {
    $env:msvc = 12
} ElseIf ($msvc -eq 2015) {
    $env:msvc = 14
} ElseIf ($msvc -eq 2017) {
    $env:msvc = 15
}

$python2_major_minor_version = GetMajorMinorVersion $env:python2_version
$python3_major_minor_version = GetMajorMinorVersion $env:python3_version

$logs = (git show -s --pretty=format:%b $env:appveyor_repo_tag_name) | Out-String
# AppVeyor uses "\n" as a convention for newlines in GitHub description
$git_description = $logs.Replace("`r`n", "\n")

