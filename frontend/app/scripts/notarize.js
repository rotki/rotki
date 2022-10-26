require('dotenv').config();
const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
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

  return await notarize({
    appBundleId: 'com.rotki.app',
    appPath: appPath,
    appleId: process.env.APPLEID,
    appleIdPassword: process.env.APPLEIDPASS
  })
    .then(() => {
      console.info(`\nNotarization of ${appPath} was complete\n`);
    })
    .catch(reason => {
      console.error(reason);
      return reason;
    });
};
