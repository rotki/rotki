const { platform } = require('node:os');
const process = require('node:process');

const LINUX_TARGETS = ['AppImage', 'tar.xz'];

const isCI = !!process.env.CI;
const includeDebPackage = isCI || !!process.env.LINUX_BUILD_DEB;

console.log(`\nBuilding on ${platform}: targeting ${process.arch}\n`);

if (includeDebPackage)
  LINUX_TARGETS.push('deb');

/**
 module.exports = {
 * @type {import("electron-builder").Configuration}
 * @see https://www.electron.build/configuration/configuration
 */
module.exports = {
  appId: 'com.rotki.app',
  directories: {
    output: 'build',
    buildResources: 'buildResources',
  },
  files: [
    'dist/**',
    '!node_modules/**',
  ],
  publish: {
    provider: 'github',
    vPrefixedTagName: true,
    releaseType: 'draft',
  },
  buildVersion: process.env.ROTKI_VERSION,
  // eslint-disable-next-line no-template-curly-in-string
  artifactName: '${productName}-${platform}_${arch}-v${buildVersion}.${ext}',
  extraResources: [
    {
      from: '../../build/backend',
      to: 'backend',
      filter: ['**/*'],
    },
    {
      from: '../../build/colibri/bin',
      to: 'colibri',
      filter: ['**/*'],
    },
    {
      from: './dist/vendor',
      to: 'vendor',
      filter: ['**/*'],
    },
  ],
  dmg: {
    sign: false,
  },
  nsis: {
    license: '../../LICENSE.md',
    createDesktopShortcut: false,
  },
  mac: {
    target: [
      {
        target: 'default',
      },
    ],
    category: 'public.app-category.finance',
    icon: 'public/assets/images/rotki.icns',
    ...(isCI || process.env.CERTIFICATE_OSX_APPLICATION
      ? {
          identity: 'Rotki Solutions GmbH (6H86XUVS7L)',
          hardenedRuntime: true,
          gatekeeperAssess: false,
          entitlements: 'signing/entitlements.mac.plist',
          entitlementsInherit: 'signing/entitlements.mac.plist',
        }
      : {
          identity: false,
        }),
  },
  win: {
    target: ['nsis'],
    icon: 'public/assets/images/rotki.ico',
  },
  linux: {
    target: LINUX_TARGETS,
    icon: 'public/assets/images/rotki_1024x1024.png',
    category: 'Finance',
  },
  ...(isCI ? { afterSign: 'scripts/notarize.cjs' } : {}),
};
