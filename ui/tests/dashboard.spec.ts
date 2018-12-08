import {Application, SpectronClient} from 'spectron';
import {
    closeAddYourSettingsPopup,
    createAccount,
    GLOBAL_TIMEOUT,
    initialiseSpectron,
    login,
    logout,
    METHOD_TIMEOUT,
    navigateTo
} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';
import {AccountType, UserSettingsController} from './user_settings_controller';


chai.should();
chai.use(chaiAsPromised);

describe('dashboard', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    let app: Application;
    let client: SpectronClient;
    let controller: UserSettingsController;

    let username: string;
    const password: string = process.env.PASSWORD as string;

    const ethAccount: string = process.env.ETH_ADDRESS as string;
    const btcAccount: string = process.env.BTC_ADDRESS as string;

    before(async () => {
        username = Guid.newGuid().toString();
        app = initialiseSpectron();
        await app.start();
        await createAccount(app, username, password);
        client = app.client;

        controller = new UserSettingsController(client);
        await client.waitUntilTextExists('.page-header', 'Dashboard', METHOD_TIMEOUT);
    });

    after(async () => {
        if (app && app.isRunning()) {
            await app.stop();
        }
    });

    it('should be originally empty', async () => {
        await client.waitForVisible('#table_balances_total_body', METHOD_TIMEOUT);
        await client.getText('.dataTables_empty').should.eventually.contain('No data available in table');
    });

    describe('after adding the accounts', () => {
        const apiKey = process.env.BITTREX_API_KEY as string;
        const apiSecret = process.env.BITTREX_API_SECRET as string;

        before(async () => {
            await navigateTo(client, '#user_settings_button');
            await closeAddYourSettingsPopup(client);

            await client.waitForVisible('#blockchain_balances_panel_body', METHOD_TIMEOUT);

            await controller.addAccount(AccountType.ETH, ethAccount);
            await controller.addAccount(AccountType.BTC, btcAccount);

            await client.waitForExist('#btcchain_per_account_table', METHOD_TIMEOUT);

            await controller.addFiatValue();
            await controller.addExchange(apiKey, apiSecret);

            await navigateToDashboard(client);

            await logout(client);
            await login(client, username, password);
        });

        it('should show the information to the user', async () => {
            await client.waitForExist('#blockchain_box', METHOD_TIMEOUT);
            await client.waitForExist('#banks_box', METHOD_TIMEOUT);
            await client.waitForExist('#bittrex_box', METHOD_TIMEOUT);
            await client.waitForExist('#table_balances_total_body > tr:nth-child(3)');

            await client.click('#table_balances_total > thead > tr > th:nth-child(1)');

            await client.getText('#table_balances_total_body > tr:nth-child(1) > td:nth-child(1)').should.eventually.contain('BTC');
            await client.getText('#table_balances_total_body > tr:nth-child(2) > td:nth-child(1)').should.eventually.contain('ETH');
            await client.getText('#table_balances_total_body > tr:nth-child(3) > td:nth-child(1)').should.eventually.contain('USD');
        });
    });
});

async function navigateToDashboard(client: SpectronClient) {
    await client.click('#side-menu > li');
    await client.waitUntilTextExists('.page-header', 'Dashboard', METHOD_TIMEOUT);
}
