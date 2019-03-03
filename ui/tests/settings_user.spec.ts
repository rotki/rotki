import {Application, SpectronClient} from 'spectron';
import {
    captureOnFailure,
    closeAddYourSettingsPopup,
    createAccount,
    GLOBAL_TIMEOUT,
    initialiseSpectron,
    METHOD_TIMEOUT,
    navigateTo,
    setupTest
} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';
import {AccountType, UserSettingsController} from './user_settings_controller';

chai.should();
chai.use(chaiAsPromised);

describe('user settings', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    this.retries(3);
    const title = this.title;

    let app: Application;
    let client: SpectronClient;

    let controller: UserSettingsController;

    let username: string;
    const password: string = process.env.PASSWORD as string;

    const ethAccount: string = process.env.ETH_ADDRESS as string;
    const btcAccount: string = process.env.BTC_ADDRESS as string;

    before(async function () {
        username = Guid.newGuid().toString();
        app = initialiseSpectron();
        await app.start();
        client = app.client;

        await setupTest(app, title, async () => {
            await createAccount(app, username, password);

            controller = new UserSettingsController(client);

            await navigateTo(client, '#user_settings_button');
            await closeAddYourSettingsPopup(client);
            await client.waitForVisible('#blockchain_balances_panel_body', METHOD_TIMEOUT);
            // navigate to accounting settings and then back to user settings to
            // try and recreate https://github.com/rotkehlchenio/rotkehlchen/issues/320
            await navigateTo(client, '#accounting_settings_button');
            await client.waitUntilTextExists('.page-header', 'Accounting Settings', METHOD_TIMEOUT);
            await navigateTo(client, '#user_settings_button');
            await client.waitForVisible('#blockchain_balances_panel_body', METHOD_TIMEOUT);

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

    it('should add an ETH account and view the account balance', async () => {
        await controller.addAccount(AccountType.ETH, ethAccount);

        const blockchain = 'ETH';
        await client.waitForExist('#ethchain_per_account_table', METHOD_TIMEOUT);
        await client.scroll('#ethchain_per_account_table', 0, 0);
        await client.getText('#ethchain_per_account_table > tbody > tr:nth-child(1) > td:nth-child(1)')
            .should
            .eventually
            .equal(ethAccount);
        await client.getText('#ethchain_per_account_table > thead > tr:nth-child(1) > th:nth-child(2)')
            .should
            .eventually
            .contain(blockchain);
        await client.getText('#blockchain_per_asset_table > tbody > tr:nth-child(1) > td:nth-child(1)')
            .should
            .eventually
            .contain(blockchain);

        const assetTableColumn = client.getText('#blockchain_per_asset_table_body > tr:nth-child(1) > td:nth-child(3)');
        await assetTableColumn.should.eventually.satisfy((value: string) => {
            return parseFloat(value) >= 0;
        }, 'The usd value should be equal or greater than zero');
    });

    it('should add a token and see that the tokens are updated', async () => {

        await client.scroll('#eth_tokens_select');

        await client.waitForEnabled('#eth_tokens_select', METHOD_TIMEOUT);
        await client.scroll('span=RDN', 0, 0);
        await client.click('span=RDN');

        await client.element('.ms-selection').getText('span=RDN').should.eventually.equal('RDN');

        await client.waitUntil(async () => {
            return client.getText('#blockchain_per_asset_table > tbody > tr:nth-child(2) > td:nth-child(1)')
                .should
                .eventually
                .contain('RDN');
        }, METHOD_TIMEOUT, 'Asset Table should contain the RDN token');
    });

    it('should add a btc account and see that it is added', async () => {

        await controller.addAccount(AccountType.BTC, btcAccount);

        const blockchain = 'BTC';

        await client.waitForExist('#btcchain_per_account_table', METHOD_TIMEOUT);
        await client.scroll('#btcchain_per_account_table');
        await client.waitUntil(async () => {
            return client.getText('#btcchain_per_account_table > tbody > tr:nth-child(1) > td:nth-child(1)')
                .should
                .eventually
                .equal(btcAccount);
        }, METHOD_TIMEOUT, 'btcchain_per_account_table should have the BTC account');

        await client.waitUntil(async () => {
            return await client.getText('#blockchain_per_asset_table > tbody > tr:nth-child(3) > td:nth-child(1)')
                .should
                .eventually
                .contain(blockchain);
        }, METHOD_TIMEOUT, 'blockchain_per_asset_table should have a BTC entry');

        const assetTableColumn = client.getText('#blockchain_per_asset_table_body > tr:nth-child(3) > td:nth-child(3)');
        await assetTableColumn.should.eventually.satisfy((value: string) => {
            return parseFloat(value) >= 0;
        }, 'The usd value should be equal or greater than zero');
    });

    it('should add a fiat balance and see that it is properly added', async () => {

        await controller.addFiatValue();

        await app.client.waitUntil(async () => {
            return client.getText('#fiat_balances_table_body > tr:nth-child(1) > td:nth-child(1)').should.eventually.contain('USD');
        }, METHOD_TIMEOUT, 'USD should appear in the #fiat_balances_table_body');

        const amountColumn = client.getText('#fiat_balances_table_body > tr:nth-child(1) > td:nth-child(2)');
        await amountColumn.should.eventually.satisfy((value: string) => {
            return parseInt(value, 10) === 50;
        }, 'The fiat amount should be equal to 50');

        const usdValueColumn = client.getText('#fiat_balances_table_body > tr:nth-child(1) > td:nth-child(3)');
        await usdValueColumn.should.eventually.satisfy((value: string) => {
            return parseInt(value, 10) === 50;
        }, 'The fiat usd_value should be equal to 50');
    });

    it('should add an exchange key and and verify that it was added', async () => {

        const apiKey = process.env.BITTREX_API_KEY as string;
        const apiSecret = process.env.BITTREX_API_SECRET as string;

        await controller.addExchange(apiKey, apiSecret);

        await client.waitForExist('#bittrex_badge', METHOD_TIMEOUT);

        await client.click('#setup_exchange');
        await client.element('#setup_exchange').click('option=bittrex');

        await app.client.waitForEnabled('#api_key_entry', METHOD_TIMEOUT, true);
        await app.client.waitForEnabled('#api_secret_entry', METHOD_TIMEOUT, true);
    });

    it('should change the currency and verify that it changed', async () => {

        await client.click('.navbar > .nav > li.dropdown:last-child');
        await client.waitForVisible('.currency-dropdown', METHOD_TIMEOUT);
        await client.click('#change-to-eur');

        await app.client.waitUntil(async () => {
            return client.getText('#fiat_balances_table > thead > tr > th:last-child')
                .should
                .eventually
                .contain('EUR');
        }, METHOD_TIMEOUT, 'fiat_balances_table should have EUR on the header');

        await client.waitUntil(async () => {
            return client.getText('#blockchain_per_asset_table > thead > tr > th:last-child')
                .should
                .eventually
                .contain('EUR');
        }, METHOD_TIMEOUT, 'blockchain_per_asset_table should have EUR on the header');

        await client.waitUntil(async () => {
            return client.getText('#ethchain_per_account_table > thead > tr > th:nth-child(3)')
                .should
                .eventually
                .contain('EUR');
        }, METHOD_TIMEOUT, 'ethchain_per_account_table should have EUR on the header');

        await client.waitUntil(async () => {
            return client.getText('#btcchain_per_account_table > thead > tr > th:last-child')
                .should
                .eventually
                .contain('EUR');
        }, METHOD_TIMEOUT, 'btcchain_per_account_table should had EUR on the header');

    });
});
