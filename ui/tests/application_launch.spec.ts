// Nice overview for electron tests with the chai.should model:
// https://dzone.com/articles/write-automated-tests-for-electron-with-spectron-m

import {Application} from 'spectron';
import * as chaiAsPromised from 'chai-as-promised';
import * as chai from 'chai';
import {captureOnFailure, GLOBAL_TIMEOUT, initialiseSpectron} from './common';

chai.should();
chai.use(chaiAsPromised);

describe('application launch', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    let app: Application;

    beforeEach(async () => {
        app = initialiseSpectron();
        await app.start();
    });

    afterEach(async function () {
        if (app && app.isRunning()) {
            await app.stop();
        }

        await captureOnFailure(app, this.currentTest);
    });

    it('assert we got 1 window running', () => {
        return app.client.getWindowCount().should.eventually.equal(1);
    });

    it('make sure we get the login popup', () => {
        return app.client.waitForExist('.jconfirm-box-container', 5000).should.eventually.equal(true);
    });

});
