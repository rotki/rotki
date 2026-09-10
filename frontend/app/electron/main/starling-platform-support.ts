import * as os from 'node:os';

/** rotki's macOS floor is High Sierra, which is Darwin 17. */
const MIN_DARWIN_MAJOR = 17;

/** rotki's Windows floor, Windows 10, which reports release `10.0` (Windows 7 to 8.1 report `6.x`). */
const MIN_WINDOWS_RELEASE = 10;

export function isMacOsVersionSupported(): boolean {
  if (os.platform() !== 'darwin')
    return true;

  const release = os.release();
  const minorStart = release.indexOf('.');
  const majorVersion = Number.parseInt(minorStart === -1 ? release : release.slice(0, minorStart));
  return majorVersion >= MIN_DARWIN_MAJOR;
}

export function isWindowsVersionSupported(): boolean {
  if (os.platform() !== 'win32')
    return true;

  const parts = os.release().split('.');
  if (parts.length > 1)
    return Number.parseInt(parts[0]) + Number.parseInt(parts[1]) * 0.1 >= MIN_WINDOWS_RELEASE;

  return true;
}
