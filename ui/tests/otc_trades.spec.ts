import {Application, SpectronClient} from 'spectron';
import {
    captureOnFailure,
    createAccount,
    GLOBAL_TIMEOUT,
    initialiseSpectron,
    METHOD_TIMEOUT,
    setupTest
} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';
import OtcController, {otcData} from './otc_controller';

const retry = require('promise-retry');
chai.should();
chai.use(chaiAsPromised);

describe('otc trades', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);

    const title = this.title;
    let app: Application;
    let client: SpectronClient;

    let username: string;
    const password: string = process.env.PASSWORD as string;
    let controller: OtcController;

    before(async function () {
        username = Guid.newGuid().toString();
        app = initialiseSpectron();
        await app.start();

        await setupTest(app, title, async () => {
            await createAccount(app, username, password);
            client = app.client;
            controller = new OtcController(client);

            await retry(async () => {
                await client.click('#side-menu>li:nth-child(2)');
            });

            await client.waitUntilTextExists('a', 'OTC Trades', METHOD_TIMEOUT);

            await retry(async () => {
                await client.click('#side-menu>li:nth-child(2)>.nav>li');
            });

            await client.waitUntilTextExists('.page-header', 'OTC Trades Management', METHOD_TIMEOUT);
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

    it('should add two OTC trades and show them on the table', async function () {
        await controller.addTrade(otcData[0]);
        await controller.addTrade(otcData[1]);
        const matchedElements = (await client.elements('#table_otctrades > tbody > tr')).value;
        const numberOfElements = matchedElements.length;
        numberOfElements.should.equal(2, 'there should be two entries');

        await client.getText('#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(2)').should.eventually.contain('BTC_EUR');
        await client.getText('#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(4)').should.eventually.contain('82');
        await client.getText('#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(5)').should.eventually.contain('268.678317859');
        await client.getText('#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(6)').should.eventually.contain('08/10/2015 10:48');
    });

    it('should edit a trade and show the edit changes on the table', async function () {
        await client.element('#table_otctrades > tbody > tr:nth-child(1)').rightClick();
        await client.click('.context-menu-list > li:first-child');
        await retry(async function () {
            await client.clearElement('#otc_amount');
        });
        await retry(async function () {
            await client.addValue('#otc_amount', 120);
        });
        await retry(async function () {
            await client.click('#otctradesubmit');
        });
        await controller.closeSuccessDialog();

        await client.getText('#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(4)').should.eventually.contain('120');
    });

    it('should delete an otc trade and the trade should be removed', async function () {
        await client.element('#table_otctrades > tbody > tr:nth-child(1)').rightClick();
        await client.click('.context-menu-list > li:nth-child(2)');

        await controller.closeSuccessDialog();

        const matchedElements = (await client.elements('#table_otctrades > tbody > tr')).value;
        const numberOfElements = matchedElements.length;
        numberOfElements.should.equal(1, 'there should be one entry left');
    });
});
