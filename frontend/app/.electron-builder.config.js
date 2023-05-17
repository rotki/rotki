const { platform } = require("os");

const MACOS_ARCHS = ['x64', 'arm64'];
const LINUX_TARGETS = ["AppImage", "tar.xz"];

const isCI = !!process.env.CI;
const macOsArch = process.env.MACOS_ELECTRON_ARCH;
const includeDebPackage = isCI || !!process.env.LINUX_BUILD_DEB;

const targetMacArch = MACOS_ARCHS.includes(macOsArch)? macOsArch : null

const isMac = platform() === 'darwin'

console.log(`\nBuilding on ${platform}: targeting ${targetMacArch}\n`)

if (includeDebPackage) {
  LINUX_TARGETS.push("deb");
}
/**
 * @type {import("electron-builder").Configuration}
 * @see https://www.electron.build/configuration/configuration
 */
const config = {
  appId: "com.rotki.app",
  directories: {
    output: "build",
    buildResources: "buildResources"
  },
  files: [
    'dist/**',
    '!node_modules/**',
    'node_modules/csv'
  ],
  publish: {
    provider: "github",
    vPrefixedTagName: true,
    releaseType: "draft"
  },
  buildVersion: process.env.ROTKI_VERSION,
  artifactName:
    "${productName}-${platform}_${arch}-v${buildVersion}.${ext}",
  extraResources: [
    {
      from: "../../build/backend",
      to: "backend",
      filter: ["**/*"]
    },
    {
      from: isMac && !targetMacArch ? "../../build/colibri/bin/${arch}" : "../../build/colibri/bin",
      to: "colibri",
      filter: ["**/*"]
    }
  ],
  dmg: {
    sign: false
  },
  nsis: {
    license: "../../LICENSE.md",
    createDesktopShortcut: false
  },
  mac: {
    target: [
      {
        target: "default",
        arch: targetMacArch ? [targetMacArch] : MACOS_ARCHS
      }
    ],
    category: "public.app-category.finance",
    icon: "public/assets/images/rotki.icns",
    ...(isCI || process.env.CERTIFICATE_OSX_APPLICATION
      ? {
        identity: "Rotki Solutions GmbH (6H86XUVS7L)",
        hardenedRuntime: true,
        gatekeeperAssess: false,
        entitlements: "signing/entitlements.mac.plist",
        entitlementsInherit: "signing/entitlements.mac.plist"
      }
      : {
        identity: false
      })
  },
  win: {
    target: ["nsis"],
    icon: "public/assets/images/rotki.ico"
  },
  linux: {
    target: LINUX_TARGETS,
    icon: "public/assets/images/rotki_1024x1024.png",
    category: "Finance"
  },
  ...(isCI ? { afterSign: "scripts/notarize.js" } : {})
};

module.exports = config;
