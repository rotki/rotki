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
import { Guid } from '../../common/guid';
import {
  AccountType,
  AccountBalancesController
} from './support/account-balances-controller';

jest.setTimeout(GLOBAL_TIMEOUT);

describe('blockchain accounts', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let controller: AccountBalancesController;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  const ethAccount: string = process.env.ETH_ADDRESS as string;
  const btcAccount: string = process.env.BTC_ADDRESS as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);
    await setupTest(application, 'blockchain_accounts', async () => {
      await createAccount(application, username, password);

      controller = new AccountBalancesController(client);

      await navigateTo(client, '.navigation__accounts-balances');

      await client.waitForVisible('.accounts-balances', METHOD_TIMEOUT);
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async () => {
    await captureOnFailure(application);
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
    await client.scroll('.token-track__search', 0, -400);

    await client.waitForEnabled(
      '.token-track__search input[type="text"]',
      METHOD_TIMEOUT
    );
    await client.addValue('.token-track__search input[type="text"]', 'RDN');
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

  test('change the currency and verify that it changed in the tables', async () => {
    await client.waitForVisible('.currency-dropdown', METHOD_TIMEOUT);
    await client.click('.currency-dropdown');
    await client.waitForVisible('#change-to-eur', METHOD_TIMEOUT);
    await client.click('#change-to-eur');
    await client.waitForVisible('#change-to-eur', METHOD_TIMEOUT, false);
    await client.pause(400);
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
