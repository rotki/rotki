import type { AfterPackContext, Configuration } from 'electron-builder';
import { platform } from 'node:os';
import process from 'node:process';
import { notarize } from '@electron/notarize';
import consola from 'consola';
import { config } from 'dotenv';

const LINUX_TARGETS = ['AppImage', 'tar.xz'];

const isCI = !!process.env.CI;
const includeDebPackage = isCI || !!process.env.LINUX_BUILD_DEB;

console.log(`\nBuilding on ${platform()}: targeting ${process.arch}\n`);

if (includeDebPackage)
  LINUX_TARGETS.push('deb');

async function afterSign(context: AfterPackContext): Promise<void> {
  config();
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') {
    consola.info('Notarization is only supported on macOS');
    return;
  }

  if (!process.env.APPLEID || !process.env.APPLEIDPASS || !process.env.IDENTITY) {
    consola.warn('APPLEID, or APPLEIDPASS or IDENTITY is not set, notarization will be skipped');
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  consola.info(`\nPreparing to notarize the application: ${appPath}\n`);

  try {
    await notarize({
      appPath,
      appleId: process.env.APPLEID,
      appleIdPassword: process.env.APPLEIDPASS,
      teamId: process.env.IDENTITY,
    });
    consola.info(`\nNotarization of ${appPath} was complete\n`);
  }
  catch (error) {
    consola.error(error);
    process.exit(1);
  }
}

/**
 module.exports = {
 * @type {import("electron-builder").Configuration}
 * @see https://www.electron.build/configuration/configuration
 */
export default {
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
  extraResources: [{
    from: '../../build/backend',
    to: 'backend',
    filter: ['**/*'],
  }, {
    from: '../../build/colibri/bin',
    to: 'colibri',
    filter: ['**/*'],
  }, {
    from: './dist/vendor',
    to: 'vendor',
    filter: ['**/*'],
  }],
  dmg: {
    sign: false,
  },
  nsis: {
    license: '../../LICENSE.md',
    createDesktopShortcut: false,
  },
  mac: {
    target: [{
      target: 'default',
    }],
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
          identity: null,
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
  ...(isCI ? { afterSign } : {}),
} satisfies Configuration;
