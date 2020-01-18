import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  selectFromUserMenu,
  setupTest
} from './utils/common';
import { Guid } from './utils/guid';

const retry = require('promise-retry');

async function dismissSuccessDialog(client: SpectronClient, message: string) {
  await client.waitUntilTextExists(
    '.jconfirm-title',
    'Success',
    METHOD_TIMEOUT
  );
  await expect(
    client.element('.jconfirm-content > div').getText()
  ).resolves.toMatch(message);

  await client.click('.jconfirm-buttons > button');
  await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);
}

jest.setTimeout(GLOBAL_TIMEOUT);

describe('accounting settings', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);

    await setupTest(application, 'accounting settings', async () => {
      await createAccount(application, username, password);
      client = application.client;

      await retry(async () => {
        await selectFromUserMenu(client, '#accounting_settings_button');
      });
      await client.waitUntilTextExists(
        '.page-header',
        'Accounting Settings',
        METHOD_TIMEOUT
      );
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async () => {
    await captureOnFailure(application);
  });

  it('should change take into account crypto 2 crypto trades', async () => {
    const message = 'Succesfully set crypto to crypto consideration value';
    await client.element('//input[@name="crypto2crypto"][@value="No"]').click();
    await dismissSuccessDialog(client, message);

    await client
      .element('//input[@name="crypto2crypto"][@value="Yes"]')
      .click();
    await dismissSuccessDialog(client, message);
  });

  it('should change take into account ethereum gas costs options', async () => {
    const message = 'Succesfully set Ethereum gas costs value';

    await client
      .element('//input[@name="include_gas_costs"][@value="No"]')
      .click();
    await dismissSuccessDialog(client, message);

    await client
      .element('//input[@name="include_gas_costs"][@value="Yes"]')
      .click();
    await dismissSuccessDialog(client, message);
  });

  it('should change tax free period status', async () => {
    const message = 'Succesfully set trade settings';
    await client
      .element('//input[@name="taxfree_period_exists"][@value="No"]')
      .click();

    await client.clearElement('#taxfree_period_entry');
    await client.addValue('#taxfree_period_entry', 150);
    await client.click('#modify_trade_settings');
    await dismissSuccessDialog(client, message);

    await client
      .element('//input[@name="taxfree_period_exists"][@value="Yes"]')
      .click();

    await client.clearElement('#taxfree_period_entry');
    await client.addValue('#taxfree_period_entry', 120);
    await client.click('#modify_trade_settings');
    await dismissSuccessDialog(client, message);
  });

  it('should be able to add and remove ignored assets', async () => {
    let matchedElements = (
      await client.elements('#ignored_assets_selection > option')
    ).value;

    expect(matchedElements.length).toEqual(1);

    await addIgnoredAsset(client, 'BSV');
    await addIgnoredAsset(client, 'GNT');

    matchedElements = (
      await client.elements('#ignored_assets_selection > option')
    ).value;

    expect(matchedElements.length).toEqual(3);

    await removeIgnoredAsset(client, 'BSV');
    await client.waitForExist('//option[@value="BSV"]', METHOD_TIMEOUT, true);
    await removeIgnoredAsset(client, 'GNT');
    await client.waitForExist('//option[@value="GNT"]', METHOD_TIMEOUT, true);

    matchedElements = (
      await client.elements('#ignored_assets_selection > option')
    ).value;
    expect(matchedElements.length).toEqual(1);
  });
});

async function removeIgnoredAsset(client: SpectronClient, asset: string) {
  await client.selectByValue('#ignored_assets_selection', asset);
  await expect(client.getValue('#ignored_asset_entry')).resolves.toEqual(asset);
  await expect(client.getText('#modify_ignored_asset_button')).resolves.toEqual(
    'Remove'
  );
  await client.click('#modify_ignored_asset_button');
}

async function addIgnoredAsset(client: SpectronClient, asset: string) {
  await client.clearElement('#ignored_asset_entry');
  await client.scroll('#ignored_assets_selection');
  await client.addValue('#ignored_asset_entry', asset);
  await expect(client.getText('#modify_ignored_asset_button')).resolves.toEqual(
    'Add'
  );

  await client.click('#modify_ignored_asset_button');
  await client.waitUntil(
    async () => {
      return client.getValue('#ignored_assets_selection') === asset;
    },
    METHOD_TIMEOUT,
    'Wait until selected value changes after add'
  );
}
