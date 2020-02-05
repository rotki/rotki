import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  setupTest
} from './utils/common';
import OtcController, { otcData } from './support/otc_controller';
import { Guid } from './utils/guid';

const retry = require('promise-retry');

jest.setTimeout(GLOBAL_TIMEOUT);

describe.skip('otc trades', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let username: string;
  const password: string = process.env.PASSWORD as string;
  let controller: OtcController;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);

    await setupTest(application, 'otc trades', async () => {
      await createAccount(application, username, password);
      controller = new OtcController(client);

      await retry(async () => {
        await client.click('#side-menu>li:nth-child(2)');
      });

      await client.waitUntilTextExists('a', 'OTC Trades', METHOD_TIMEOUT);

      await retry(async () => {
        await client.click('#side-menu>li:nth-child(2)>.nav>li');
      });

      await client.waitUntilTextExists(
        '.page-header',
        'OTC Trades Management',
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

  it('should add two OTC trades and show them on the table', async () => {
    await controller.addTrade(otcData[0]);
    await controller.addTrade(otcData[1]);
    const matchedElements = (
      await client.elements('#table_otctrades > tbody > tr')
    ).value;

    expect(matchedElements.length).toEqual(2);

    await expect(
      client.getText(
        '#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(2)'
      )
    ).resolves.toContain('BTC_EUR');
    await expect(
      client.getText(
        '#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(4)'
      )
    ).resolves.toContain('82');
    await expect(
      client.getText(
        '#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(5)'
      )
    ).resolves.toContain('268.678317859');
    await expect(
      client.getText(
        '#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(6)'
      )
    ).resolves.toContain('08/10/2015 10:48');
  });

  it('should edit a trade and show the edit changes on the table', async () => {
    await client
      .element('#table_otctrades > tbody > tr:nth-child(1)')
      .rightClick();
    await client.click('.context-menu-list > li:first-child');
    await retry(async () => {
      await client.clearElement('#otc_amount');
    });
    await retry(async () => {
      await client.addValue('#otc_amount', 120);
    });
    await retry(async () => {
      await client.click('#otctradesubmit');
    });
    await controller.closeSuccessDialog();

    await expect(
      client.getText(
        '#table_otctrades > tbody > tr:nth-child(1) > td:nth-child(4)'
      )
    ).resolves.toContain('120');
  });

  it('should delete an otc trade and the trade should be removed', async () => {
    await client
      .element('#table_otctrades > tbody > tr:nth-child(1)')
      .rightClick();
    await client.click('.context-menu-list > li:nth-child(2)');

    await controller.closeSuccessDialog();

    const matchedElements = (
      await client.elements('#table_otctrades > tbody > tr')
    ).value;

    await expect(matchedElements.length).resolves.toEqual(1);
  });
});
