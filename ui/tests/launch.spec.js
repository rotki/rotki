// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

const {
    path, chai, Application, electronPath
} = require('./utils/setup')

const guid = () => {
    const s4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1)
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

describe('Application launch', function () {
  this.timeout(30000);

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

  it('make sure we get the login popup', function () {
    return this.app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);
  });

});
