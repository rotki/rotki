// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const Application = require('spectron').Application;
const electronPath = require('electron'); // Require Electron from the binaries included in node_modules.
const path = require('path');
const chaiAsPromised = require("chai-as-promised");
const chai = require("chai");
chai.should();
chai.use(chaiAsPromised);

describe('Application launch', function () {
    this.timeout(10000);

  beforeEach(function () {
    this.app = new Application({
      path: electronPath,
      args: [path.join(__dirname, '../..')]
    });
      return this.app.start();
  });

  afterEach(function () {
    if (this.app && this.app.isRunning()) {
        return this.app.stop();
    }
  });

  it('assert we got 1 window running', function () {
      return this.app.client.getWindowCount().should.eventually.equal(1);
  });

    it('make sure we get the loging popup', function () {
        return this.app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);
    });

    it('Going to the user settings, adding an ethereum account and looking at its balance', function () {

    });

    it('Adding a token and seeing the tokens get updated', function () {

    });

    it('Adding a bitcoin account and seeing that the balance is there', function () {

    });
    it('adding a fiat balance and see that it is properly updated', function () {

    });
    it('add an exchange and see that the api key is successfully accepted', function () {

    });
    it('change the currency to EUR and the currency changes everywhere in the UI', function () {

    });
    it('change each one of the settings and see the change has been applied', function () {

    });

});
