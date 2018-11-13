import {Application, SpectronClient} from 'spectron';
import {createAccount, GLOBAL_TIMEOUT, initialiseSpectron, METHOD_TIMEOUT, navigateTo} from './common';
import * as chai from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import {Guid} from './guid';
import {expect} from 'chai';

chai.should();
chai.use(chaiAsPromised);

async function dismissSuccessDialog(client: SpectronClient, message: string) {
    await client.waitUntilTextExists('.jconfirm-title', 'Success', METHOD_TIMEOUT);
    await client.element('.jconfirm-content > div').getText().should.eventually.contain(message);
    await client.click('.jconfirm-buttons > button');
    await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);
}

describe('accounting settings', function () {
    // @ts-ignore
    this.timeout(GLOBAL_TIMEOUT);
    let app: Application;
    let client: SpectronClient;

    let username: string;
    const password: string = process.env.PASSWORD as string;

    before(async () => {
        username = Guid.newGuid().toString();
        app = initialiseSpectron();
        await app.start();
        await createAccount(app, username, password);
        client = app.client;

        await navigateTo(client, '#accounting_settings_button');

        await client.waitUntilTextExists('.page-header', 'Accounting Settings', METHOD_TIMEOUT);
    });

    after(async () => {
        if (app && app.isRunning()) {
            await app.stop();
        }
    });

    it('should change take into account crypto 2 crypto trades', async () => {
        const message = 'Succesfully set crypto to crypto consideration value';
        await client.element('//input[@name="crypto2crypto"][@value="No"]').click();
        await dismissSuccessDialog(client, message);

        await client.element('//input[@name="crypto2crypto"][@value="Yes"]').click();
        await dismissSuccessDialog(client, message);
    });

    it('should change take into account ethereum gas costs options', async () => {
        const message = 'Succesfully set Ethereum gas costs value';

        await client.element('//input[@name="include_gas_costs"][@value="No"]').click();
        await dismissSuccessDialog(client, message);

        await client.element('//input[@name="include_gas_costs"][@value="Yes"]').click();
        await dismissSuccessDialog(client, message);
    });

    it('should change tax free period status', async () => {
        const message = 'Succesfully set trade settings';
        await client.element('//input[@name="taxfree_period_exists"][@value="No"]').click();

        await client.clearElement('#taxfree_period_entry');
        await client.addValue('#taxfree_period_entry', 150);
        await client.click('#modify_trade_settings');
        await dismissSuccessDialog(client, message);

        await client.element('//input[@name="taxfree_period_exists"][@value="Yes"]').click();

        await client.clearElement('#taxfree_period_entry');
        await client.addValue('#taxfree_period_entry', 120);
        await client.click('#modify_trade_settings');
        await dismissSuccessDialog(client, message);
    });

    it('should be able to add and remove ignored assets', async () => {
        const selection = 'Click to see all ignored assets and select one for removal';
        await client.scroll('#ignored_assets_selection');

        const elements = (await client.elements('#ignored_assets_selection > option')).value.length;
        expect(elements).to.be.equal(1, 'There should only be only one option in #ignored_assets_selection');
        await client.getText('#ignored_assets_selection > option')
            .should
            .eventually
            .equal(selection, 'Should only contain the default message');

        await client.addValue('#ignored_asset_entry', 'KTT');

        await client.getText('#modify_ignored_asset_button')
            .should
            .eventually
            .equal('Add', 'Button should have the label add');

        await client.click('#modify_ignored_asset_button');

        await client.waitUntil(async () => {
            return client.getValue('#ignored_assets_selection').should.eventually.equal('KTT');
        }, METHOD_TIMEOUT, 'Wait until selected value changes after delete');

        await client.clearElement('#ignored_asset_entry');
        await client.addValue('#ignored_asset_entry', 'TTT');

        await client.click('#modify_ignored_asset_button');

        await client.getValue('#ignored_asset_entry')
            .should
            .eventually
            .equal('TTT');

        await client.selectByValue('#ignored_assets_selection', 'KTT');
        await client.getValue('#ignored_asset_entry')
            .should
            .eventually
            .equal('KTT');

        await client.getValue('#ignored_asset_entry');

        await client.getText('#modify_ignored_asset_button')
            .should
            .eventually
            .equal('Remove', 'Button should have the label Remove');

        await client.click('#modify_ignored_asset_button');

        await client.getValue('#ignored_assets_selection').should.eventually.equal('');

        const options = (await client.elements('#ignored_assets_selection > option')).value.length;
        expect(options).to.be.equal(2, 'There should only be only two option in #ignored_assets_selection');

        await client.selectByIndex('#ignored_assets_selection', 0);
        await client.getValue('#ignored_asset_entry')
            .should
            .eventually
            .equal('');
    });
});
