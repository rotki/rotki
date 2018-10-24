import {Application} from 'spectron';
import {createAccount, GLOBAL_TIMEOUT, initialiseSpectron, METHOD_TIMEOUT} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';

chai.should();
chai.use(chaiAsPromised);

describe('first usage', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    let app: Application;

    beforeEach(async () => {
        app = initialiseSpectron();
        await app.start();
    });

    afterEach(async () => {
        if (app && app.isRunning()) {
            await app.stop();
        }
    });

    it('create account', async () => {
        const username: string = Guid.newGuid().toString();
        const password: string = process.env.PASSWORD as string;

        await createAccount(app, username, password);

        await app.client.click('#user-dropdown');
        await app.client.waitForVisible('#logout_button', METHOD_TIMEOUT);
        await app.client.click('#logout_button');

        await app.client.waitForVisible('.jconfirm', METHOD_TIMEOUT);
        await app.client.click('.jconfirm-buttons>button');

        await app.client.waitForVisible('.jconfirm', METHOD_TIMEOUT);
    });
});
