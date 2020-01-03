import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  login,
  logout,
  METHOD_TIMEOUT,
  navigateTo,
  setupTest
} from './utils/common';
import { Guid } from './utils/guid';
const retry = require('promise-retry');

jest.setTimeout(GLOBAL_TIMEOUT);

describe('general settings', () => {
  let application: Application;
  let client: SpectronClient;
  let stop: () => Promise<Application>;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);
    await setupTest(application, 'general settings', async () => {
      await createAccount(application, username, password);
      await navigateTo(client, '.user-dropdown__accounting-settings');
      await client.waitUntilTextExists(
        '.page-header',
        'Settings',
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

  it('should change the general settings and save them', async () => {
    await retry(async () => {
      client.clearElement('#eth_rpc_endpoint');
    });
    await retry(async () => {
      client.addValue('#eth_rpc_endpoint', 9001);
    });

    await retry(async () => {
      client.clearElement('#floating_precision');
    });
    await retry(async () => {
      client.addValue('#floating_precision', 4);
    });

    await retry(async () => {
      client.clearElement('#balance_save_frequency');
    });
    await retry(async () => {
      client.addValue('#balance_save_frequency', 48);
    });

    await retry(async () => {
      client.click('#anonymized_logs_input');
    });

    await retry(async () => {
      client.clearElement('#historical_data_start');
    });

    await retry(async () => {
      client.addValue('#historical_data_start', '03/10/2018');
    });

    await retry(async () => {
      client.clearElement('#date_display_format');
    });

    await retry(async () => {
      client.addValue('#date_display_format', '%d-%m-%Y %H:%M:%S %z');
    });

    await client.selectByValue('#maincurrencyselector', 'JPY');

    await retry(async () => {
      client.click('#settingssubmit');
    });

    await client.waitUntilTextExists(
      '.jconfirm-title',
      'Success',
      METHOD_TIMEOUT
    );
    await expect(
      client.element('.jconfirm-content > div').getText()
    ).resolves.toMatch('Successfully modified settings.');

    await retry(async () => {
      client.click('.jconfirm-buttons > button');
    });
    await client.waitForExist('.jconfirm-box', METHOD_TIMEOUT, true);

    await logout(client);
    await login(client, username, password);

    await client.waitUntilTextExists(
      '.page-header',
      'Dashboard',
      METHOD_TIMEOUT
    );

    await navigateTo(client, '.user-dropdown__accounting-settings');

    await client.waitUntilTextExists(
      '.page-header',
      'Settings',
      METHOD_TIMEOUT
    );

    await expect(client.getValue('#floating_precision')).resolves.toEqual('4');
    await expect(client.getValue('#historical_data_start')).resolves.toEqual(
      '03/10/2018'
    );

    await expect(client.getValue('#balance_save_frequency')).resolves.toEqual(
      '48'
    );

    await expect(client.getValue('#eth_rpc_endpoint')).resolves.toEqual(
      'http://localhost:8545'
    );

    await expect(client.isSelected('#anonymized_logs_input')).resolves.toBe(
      true
    );

    await expect(client.getValue('#maincurrencyselector')).resolves.toEqual(
      'JPY'
    );
    await expect(client.getValue('#date_display_format')).resolves.toEqual(
      '%d-%m-%Y %H:%M:%S %z'
    );
  });
});
