// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

import {Application} from 'spectron';

import * as electron from 'electron';
import * as path from 'path';
import * as chaiAsPromised from 'chai-as-promised';
import * as chai from 'chai';

chai.should();
chai.use(chaiAsPromised);

function initialiseSpectron() {

    return new Application({
        path: electron as any,
        args: [path.join(__dirname, '../..')],
        env: {
            ELECTRON_ENABLE_LOGGING: true,
            ELECTRON_ENABLE_STACK_DUMPING: true,
            NODE_ENV: 'development'
        },
        startTimeout: 10000,
        chromeDriverLogPath: '../chromedriverlog.txt'
    });
}

describe('Application launch', function () {
    // @ts-ignore
    this.timeout(10000);
    let app: Application;

    beforeEach(() => {
        app = initialiseSpectron();
        return app.start();
    });

    afterEach(() => {
        if (app && app.isRunning()) {
            return app.stop();
        } else {
            return Promise.reject('app should be running');
        }
    });

    it('assert we got 1 window running', () => {
        return app.client.getWindowCount().should.eventually.equal(1);
    });

    it('make sure we get the loging popup', () => {
        // @ts-ignore
        return app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);
    });

});
