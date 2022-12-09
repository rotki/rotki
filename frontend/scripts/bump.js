const fs = require('node:fs');
const appPackage = require('rotki/package.json');
const packageLock = require('../package-lock.json');

packageLock.packages.app.version = appPackage.version;
fs.writeFileSync('../package-lock.json', JSON.stringify(packageLock, null, 2));
