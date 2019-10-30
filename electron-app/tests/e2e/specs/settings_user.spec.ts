import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  navigateTo,
  setupTest
} from './utils/common';
import { Guid } from './utils/guid';
import {
  AccountType,
  UserSettingsController
} from './support/user_settings_controller';

jest.setTimeout(GLOBAL_TIMEOUT);
jest.retryTimes(3);

describe('user settings', () => {
  let app: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let controller: UserSettingsController;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  const ethAccount: string = process.env.ETH_ADDRESS as string;
  const btcAccount: string = process.env.BTC_ADDRESS as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    const testEnvironment = await initSpectron();
    app = testEnvironment.application;
    stop = testEnvironment.stop;
    client = app.client;

    await setupTest(app, 'user settings', async () => {
      await createAccount(app, username, password);

      controller = new UserSettingsController(client);

      await navigateTo(client, '.user-dropdown__user-settings');
      await client.waitForVisible('.user-settings', METHOD_TIMEOUT);
      // navigate to accounting settings and then back to user settings to
      // try and recreate https://github.com/rotki/rotki/issues/320
      await navigateTo(client, '.user-dropdown__accounting-settings');
      await client.waitUntilTextExists(
        '.page-header',
        'Accounting Settings',
        METHOD_TIMEOUT
      );
      await navigateTo(client, '.user-dropdown__user-settings');
      await client.waitForVisible('.user-settings', METHOD_TIMEOUT);
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async function() {
    await captureOnFailure(app);
  });

  test('should add an ETH account and view the account balance', async () => {
    await controller.addAccount(AccountType.ETH, ethAccount);

    await client.waitUntilTextExists(
      '.balance-table__title',
      'ETH per account balances',
      METHOD_TIMEOUT
    );

    await client.scroll('.eth-balance-table', 0, 0);
    await client.waitForExist(
      '.eth-balance-table tbody > tr:nth-child(1) > td:nth-child(2)',
      METHOD_TIMEOUT
    );
    await expect(
      client.getText(
        '.eth-balance-table tbody > tr:nth-child(1) > td:nth-child(1)'
      )
    ).resolves.toEqual(ethAccount);
    await expect(
      client.getText(
        '.eth-balance-table thead > tr:nth-child(1) > th:nth-child(2)'
      )
    ).resolves.toMatch('ETH');
    await expect(
      client.getText(
        '.asset-balances tbody > tr:nth-child(1) > td:nth-child(1)'
      )
    ).resolves.toMatch('ETH');
    const assetTableColumn = client.getText(
      '.asset-balances tbody > tr:nth-child(1) > td:nth-child(3)'
    );
    await expect(parseFloat(await assetTableColumn)).toBeGreaterThan(0);
  });

  test('add a BTC account and see that it is added', async () => {
    await controller.addAccount(AccountType.BTC, btcAccount);

    await client.waitForExist('.btc-balance-table', METHOD_TIMEOUT);
    await client.scroll('.btc-balance-table');
    await client.waitForExist(
      '.btc-balance-table tbody > tr:nth-child(1) > td:nth-child(2)',
      METHOD_TIMEOUT
    );
    await expect(
      client.getText(
        '.btc-balance-table tbody > tr:nth-child(1) > td:nth-child(1)'
      )
    ).resolves.toEqual(btcAccount);
    await expect(
      client.getText(
        '.asset-balances tbody > tr:nth-child(2) > td:nth-child(1)'
      )
    ).resolves.toMatch('BTC');
    const assetTableColumn = client.getText(
      '.asset-balances tbody > tr:nth-child(2) > td:nth-child(3)'
    );
    await expect(parseFloat(await assetTableColumn)).toBeGreaterThanOrEqual(0);
  });

  test('should add a token and see that the tokens are updated', async () => {
    await client.scroll('.token-track__search');

    await client.waitForEnabled('.token-track__search', METHOD_TIMEOUT);
    await client.addValue('.token-track__search input', 'RDN');
    await client.click('.v-list-item__title=RDN');

    await client.waitUntilTextExists(
      '.asset-balances tbody > tr:nth-child(3) > td:nth-child(1)',
      'RDN',
      METHOD_TIMEOUT
    );

    await expect(
      client.getText(
        '.asset-balances tbody > tr:nth-child(3) > td:nth-child(1)'
      )
    ).resolves.toMatch('RDN');
  });

  it('add a fiat balance and see that it is properly added', async () => {
    await controller.addFiatValue();

    await client.waitForExist(
      '.fiat-balances tbody > tr:nth-child(1) > td:nth-child(2)',
      METHOD_TIMEOUT
    );
    await expect(
      client.getText('.fiat-balances tbody > tr:nth-child(1) > td:nth-child(1)')
    ).resolves.toMatch('USD');
    const amountColumn = client.getText(
      '.fiat-balances tbody > tr:nth-child(1) > td:nth-child(2)'
    );
    await expect(amountColumn).resolves.toMatch('50');
    const usdValueColumn = client.getText(
      '.fiat-balances tbody > tr:nth-child(1) > td:nth-child(3)'
    );
    await expect(usdValueColumn).resolves.toMatch('50');
  });

  test('add an exchange key and and verify that it was added', async () => {
    const apiKey = process.env.BITTREX_API_KEY as string;
    const apiSecret = process.env.BITTREX_API_SECRET as string;

    await controller.addExchange(apiKey, apiSecret);

    await client.scroll('.exchange-settings', 0, 0);

    client.click('.exchange-settings__fields__exchange');

    await client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
    client.element(`.v-list-item__title=bittrex`).click();

    await client.waitForVisible('.v-select-list', METHOD_TIMEOUT, false);

    await client.waitForEnabled(
      '.exchange-settings__fields__api-key input',
      METHOD_TIMEOUT,
      true
    );
    await expect(
      client.element('.exchange-settings__fields__api-key input').isEnabled()
    ).resolves.toBe(false);
    await expect(
      client.element('.exchange-settings__fields__api-secret input').isEnabled()
    ).resolves.toBe(false);
  });

  test('change the currency and verify that it changed in the tables', async () => {
    await client.waitForVisible('.currency-dropdown', METHOD_TIMEOUT);
    client.click('.currency-dropdown');
    await client.waitForVisible('#change-to-eur', METHOD_TIMEOUT);
    client.click('#change-to-eur');
    await client.waitForVisible('#change-to-eur', METHOD_TIMEOUT, false);
    await expect(
      client.getText('.fiat-balances thead > tr > th:last-child')
    ).resolves.toMatch('EUR');
    await expect(
      client.getText('.asset-balances thead > tr > th:last-child')
    ).resolves.toMatch('EUR');
    await expect(
      client.getText('.eth-balance-table thead > tr > th:nth-child(3)')
    ).resolves.toMatch('EUR');
    await expect(
      client.getText('.btc-balance-table thead > tr > th:nth-child(3)')
    ).resolves.toMatch('EUR');
  });
});
