import { Application, SpectronClient } from 'spectron';
import {
  createAccount,
  GLOBAL_TIMEOUT,
  initialiseSpectron,
  METHOD_TIMEOUT,
  navigateTo,
  setupTest,
  captureOnFailure
} from './common';
import * as chai from 'chai';
import { expect } from 'chai';
import * as chaiAsPromised from 'chai-as-promised';
import { Guid } from './guid';

const retry = require('promise-retry');
chai.should();
chai.use(chaiAsPromised);

async function dismissSuccessDialog(client: SpectronClient, message: string) {
  await client.waitUntilTextExists(
    '.jconfirm-title',
    'Success',
    METHOD_TIMEOUT
  );
  await client
    .element('.jconfirm-content > div')
    .getText()
    .should.eventually.contain(message);
  await client.click('.jconfirm-buttons > button');
  await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);
}

describe('accounting settings', function() {
  // @ts-ignore
  this.timeout(GLOBAL_TIMEOUT);
  this.retries(3);
  const title = this.title;
  let app: Application;
  let client: SpectronClient;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  before(async function() {
    username = Guid.newGuid().toString();
    app = initialiseSpectron();
    await app.start();

    await setupTest(app, title, async () => {
      await createAccount(app, username, password);
      client = app.client;

      await retry(async () => {
        await navigateTo(client, '#accounting_settings_button');
      });
      await client.waitUntilTextExists(
        '.page-header',
        'Accounting Settings',
        METHOD_TIMEOUT
      );
    });
  });

  after(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });

  afterEach(async function() {
    await captureOnFailure(app, this.currentTest);
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

  it('should be able to add and remove ignored assets', async function() {
    this.retries(0);

    let matchedElements = (await client.elements(
      '#ignored_assets_selection > option'
    )).value;
    let numberOfElements = matchedElements.length;
    expect(numberOfElements).to.be.equal(
      1,
      'First there should only be only one option in #ignored_assets_selection'
    );

    await addIgnoredAsset(client, 'BSV');
    await addIgnoredAsset(client, 'GNT');

    matchedElements = (await client.elements(
      '#ignored_assets_selection > option'
    )).value;
    numberOfElements = matchedElements.length;
    expect(numberOfElements).to.be.equal(
      3,
      'After ignoring two there should only be only three options in #ignored_assets_selection'
    );

    await removeIgnoredAsset(client, 'BSV');
    await client.waitForExist('//option[@value="BSV"]', METHOD_TIMEOUT, true);
    await removeIgnoredAsset(client, 'GNT');
    await client.waitForExist('//option[@value="GNT"]', METHOD_TIMEOUT, true);

    matchedElements = (await client.elements(
      '#ignored_assets_selection > option'
    )).value;
    numberOfElements = matchedElements.length;

    expect(numberOfElements).to.be.equal(
      1,
      'After removal there should only be only one option in #ignored_assets_selection'
    );
  });
});

async function removeIgnoredAsset(client: SpectronClient, asset: string) {
  await client.selectByValue('#ignored_assets_selection', asset);
  await client.getValue('#ignored_asset_entry').should.eventually.equal(asset);
  await client
    .getText('#modify_ignored_asset_button')
    .should.eventually.equal('Remove', 'Button should have the label Remove');
  await client.click('#modify_ignored_asset_button');
}

async function addIgnoredAsset(client: SpectronClient, asset: string) {
  await client.clearElement('#ignored_asset_entry');
  await client.scroll('#ignored_assets_selection');
  await client.addValue('#ignored_asset_entry', asset);
  await client
    .getText('#modify_ignored_asset_button')
    .should.eventually.equal('Add', 'Button should have the label add');
  await client.click('#modify_ignored_asset_button');
  await client.waitUntil(
    async () => {
      return client
        .getValue('#ignored_assets_selection')
        .should.eventually.equal(asset);
    },
    METHOD_TIMEOUT,
    'Wait until selected value changes after add'
  );
}
