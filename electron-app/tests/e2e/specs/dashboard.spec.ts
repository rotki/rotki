import { Application, SpectronClient } from 'spectron';
import {
  AccountType,
  UserSettingsController
} from './support/user_settings_controller';
import { Guid } from './utils/guid';
import {
  captureOnFailure,
  createAccount,
  initSpectron,
  login,
  logout,
  METHOD_TIMEOUT,
  selectFromUserMenu,
  setupTest
} from './utils/common';
const retry = require('promise-retry');

describe('dashboard', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;
  let controller: UserSettingsController;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  const ethAccount: string = process.env.ETH_ADDRESS as string;
  const btcAccount: string = process.env.BTC_ADDRESS as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);

    await setupTest(application, 'dashboard', async () => {
      await createAccount(application, username, password);

      controller = new UserSettingsController(client);
      await client.waitUntilTextExists(
        '.page-header',
        'Dashboard',
        METHOD_TIMEOUT
      );
    });
  });

  afterAll(async () => {
    await captureOnFailure(application);
    await stop();
  });

  it('should be originally empty', async () => {
    await client.waitForVisible('#table_balances_total_body', METHOD_TIMEOUT);
    await expect(client.getText('.dataTables_empty')).toMatch(
      'No data available in table'
    );
  });

  describe('after adding the accounts', () => {
    const apiKey = process.env.BITTREX_API_KEY as string;
    const apiSecret = process.env.BITTREX_API_SECRET as string;

    beforeAll(async () => {
      await setupTest(application, `dashboard_after_adding`, async () => {
        await retry(async () => {
          await selectFromUserMenu(client, '#user_settings_button');
        });

        await client.waitForVisible(
          '#blockchain_balances_panel_body',
          METHOD_TIMEOUT
        );

        await controller.addAccount(AccountType.ETH, ethAccount);
        await controller.addAccount(AccountType.BTC, btcAccount);

        await client.waitForExist(
          '#btcchain_per_account_table',
          METHOD_TIMEOUT
        );

        await controller.addFiatValue();
        await controller.addExchange(apiKey, apiSecret);

        await navigateToDashboard(client);

        await logout(client);
        await login(client, username, password);
      });
    });

    it('should show the information to the user', async () => {
      await client.waitForExist('#blockchain_box', METHOD_TIMEOUT);
      await client.waitForExist('#banks_box', METHOD_TIMEOUT);
      await client.waitForExist('#bittrex_box', METHOD_TIMEOUT);
      await client.waitForExist('#table_balances_total_body > tr:nth-child(3)');

      await client.click(
        '#table_balances_total > thead > tr > th:nth-child(1)'
      );

      await expect(
        client.getText(
          '#table_balances_total_body > tr:nth-child(1) > td:nth-child(1)'
        )
      ).resolves.toContain('BTC');
      await expect(
        client.getText(
          '#table_balances_total_body > tr:nth-child(2) > td:nth-child(1)'
        )
      ).resolves.toContain('ETH');
      await expect(
        client.getText(
          '#table_balances_total_body > tr:nth-child(3) > td:nth-child(1)'
        )
      ).resolves.toContain('USD');
    });
  });

  describe('navigate to statistics and back', () => {
    it('should navigate to statistics', async () => {
      await navigateToStatistics(client);
    });

    it('should navigate to dashboard', async () => {
      await navigateToDashboard(client);
    });
  });
});

async function navigateToDashboard(client: SpectronClient) {
  await retry(async () => {
    client.click('#side-menu > li');
    await client.waitUntilTextExists(
      '.page-header',
      'Dashboard',
      METHOD_TIMEOUT
    );
  });
}

async function navigateToStatistics(client: SpectronClient) {
  await retry(async () => {
    client.click('#side-menu > li:nth-child(3)');
    await client.waitUntilTextExists(
      '.page-header',
      'Statistics',
      METHOD_TIMEOUT
    );
  });
}
