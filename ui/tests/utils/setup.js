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

module.exports.waitAfterLoad = async function () {
    await this.app.client.pause(1000)

    await this.app.client.waitForExist('#user_name_entry', 5000).should.eventually.equal(true);
    
    {
        // this code exists because the IPC is failing

        await this.app.client.pause(2000)

        await this.app.client.execute(function () {
            if ($('.jconfirm').length > 1) {
                $('.jconfirm:last').remove()
            }
        })
    }
}

module.exports.waitAfterSignup = async function () {
    await this.app.client.pause(2000)

    // wait for popup modal, then close it
    await this.app.client.waitForExist('.jconfirm-box', 5000)
    await this.app.client.execute(function () {
        $('.jconfirm').remove()
    })

    await this.app.client.pause(3000)

    // wait for popup modal, then close it
    await this.app.client.waitForExist('.jconfirm-box', 5000)
    await this.app.client.execute(function () {
        $('.jconfirm').remove()
    })
}