require('dotenv').config();
const Application = require('spectron').Application;
const electronPath = require('electron'); // Require Electron from the binaries included in node_modules.
const path = require('path');
const chaiAsPromised = require("chai-as-promised");
const chai = require("chai");
chai.should();
chai.use(chaiAsPromised);

module.exports.Application = Application
module.exports.electronPath = electronPath
module.exports.path = path
module.exports.chai = chai
