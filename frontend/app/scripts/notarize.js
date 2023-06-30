require('dotenv').config();
const { notarize } = require('@electron/notarize');

exports.default = async context => {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') {
    return;
  }

  if (!process.env.APPLEID) {
    console.info('APPLEID is not set, notarization will be skipped');
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.info(`\nPreparing to notarize the application: ${appPath}\n`);

  try {
    await notarize({
      appBundleId: 'com.rotki.app',
      appPath,
      appleId: process.env.APPLEID,
      appleIdPassword: process.env.APPLEIDPASS,
      teamId: process.env.IDENTITY,
      tool: 'notarytool'
    });
    console.info(`\nNotarization of ${appPath} was complete\n`);
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
};
