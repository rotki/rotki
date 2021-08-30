const appPackage = require('./app/package.json')
const packageLock = require('./package-lock.json');
const fs = require("fs");

packageLock.packages.app.version = appPackage.version;
fs.writeFileSync('./package-lock.json', JSON.stringify(packageLock, null,2))