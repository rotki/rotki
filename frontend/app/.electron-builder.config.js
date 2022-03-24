/**
 * @type {import("electron-builder").Configuration}
 * @see https://www.electron.build/configuration/configuration
 */
const config = {
  appId: "com.rotki.app",
  directories: {
    output: 'electron-build',
    buildResources: 'buildResources',
  },
  files: [
    'dist/**',
  ],
  publish: {
    provider: "github",
    vPrefixedTagName: true,
    releaseType: "draft"
  },
  buildVersion: process.env.ROTKEHLCHEN_VERSION,
  artifactName:
    "${productName}-${platform}_${arch}-v${buildVersion}.${ext}",
  extraResources: [
    {
      from: "../../rotkehlchen_py_dist",
      to: "rotkehlchen_py_dist",
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
    category: "public.app-category.finance",
    icon: "public/assets/images/rotki.icns",
    ...(process.env.CI
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
    target: ["AppImage", "tar.xz", "deb"],
    icon: "public/assets/images/rotki_1024x1024.png",
    category: "Finance"
  },
  ...(process.env.CI ? { afterSign: "scripts/notarize.js" } : {})
};

module.exports = config;
