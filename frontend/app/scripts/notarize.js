require('dotenv').config();
const { notarize } = require('electron-notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') {
    return;
  }

  if (!process.env.APPLEID) {
    console.info('APPLEID is not set, notarization will be skipped');
    return;
  }

  console.info('Preparing to notarize the application');

  const appName = context.packager.appInfo.productFilename;

  return await notarize({
    appBundleId: 'com.rotki.app',
    appPath: `${appOutDir}/${appName}.app`,
    appleId: process.env.APPLEID,
    appleIdPassword: process.env.APPLEIDPASS
  });
};
