import {Application, SpectronClient} from 'spectron';
import {
    captureOnFailure,
    createAccount,
    GLOBAL_TIMEOUT,
    initialiseSpectron,
    login,
    logout,
    METHOD_TIMEOUT,
    navigateTo,
    setupTest
} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';
const retry = require('promise-retry');

chai.should();
chai.use(chaiAsPromised);

describe('general settings', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    this.retries(3);
    const title = this.title;

    let app: Application;
    let client: SpectronClient;

    let username: string;
    const password: string = process.env.PASSWORD as string;

    before(async function () {
        username = Guid.newGuid().toString();
        app = initialiseSpectron();
        await app.start();
        client = app.client;

        await setupTest(app, title, async () => {
            await createAccount(app, username, password);
            await navigateTo(client, '#settingsbutton');
            await client.waitUntilTextExists('.page-header', 'Settings', METHOD_TIMEOUT);
        });
    });

    after(async () => {
        if (app && app.isRunning()) {
            await app.stop();
        }
    });

    afterEach(async function () {
        await captureOnFailure(app, this.currentTest);
    });

    it('should add wrong port number and get an error', async () => {
        await retry( async() => {
            client.clearElement('#eth_rpc_port');
        });
        await retry( async() => {
            client.addValue('#eth_rpc_port', 500000);
        });
        await client.click('#settingssubmit');

        await client.waitUntilTextExists('.jconfirm-title', 'Invalid port number', METHOD_TIMEOUT);
        await client.element('.jconfirm-content > div').getText()
            .should
            .eventually
            .contain('Please ensure that the specified port number is between 1 and 65535');
        await client.click('.jconfirm-buttons > button');
        await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);
    });

    it('should change the general settings and save them', async () => {
        await retry( async() => {
            client.clearElement('#eth_rpc_port');
        });
        await retry( async() => {
            client.addValue('#eth_rpc_port', 9001);
        });

        await retry( async() => {
            client.clearElement('#floating_precision');
        });
        await retry( async() => {
            client.addValue('#floating_precision', 4);
        });

        await retry( async() => {
            client.clearElement('#balance_save_frequency');
        });
        await retry( async() => {
            client.addValue('#balance_save_frequency', 48);
        });

        await retry( async() => {
            client.click('#anonymized_logs_input');
        });

        await retry( async() => {
            client.clearElement('#historical_data_start');
        });
        await retry( async() => {
            client.addValue('#historical_data_start', '03/10/2018');
        });

        await retry( async() => {
            client.addValue('#date_display_format', '%d-%m-%Y %H:%M:%S %z');
        });

        await client.selectByValue('#maincurrencyselector', 'JPY');

        await retry( async() => {
            client.click('#settingssubmit');
        });

        await client.waitUntilTextExists('.jconfirm-title', 'Success', METHOD_TIMEOUT);
        await client.element('.jconfirm-content > div').getText()
            .should
            .eventually
            .contain('Successfully modified settings.');

        await retry( async() => {
            client.click('.jconfirm-buttons > button');
        });
        await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);

        await logout(client);
        await login(client, username, password);

        await client.waitUntilTextExists('.page-header', 'Dashboard', METHOD_TIMEOUT);

        await navigateTo(client, '#settingsbutton');

        await client.waitUntilTextExists('.page-header', 'Settings', METHOD_TIMEOUT);

        await client.getValue('#floating_precision').should.eventually.equal('4');
        await client.getValue('#historical_data_start').should.eventually.equal('03/10/2018');
        await client.getValue('#balance_save_frequency').should.eventually.equal('48');
        await client.getValue('#eth_rpc_port').should.eventually.equal('8545');
        await client.isSelected('#anonymized_logs_input').should.eventually.be.true;
        await client.getValue('#maincurrencyselector').should.eventually.equal('JPY');
        await client.getValue('#date_display_format').should.eventually.equal('%d-%m-%Y %H:%M:%S %z');
    });
});
