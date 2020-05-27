import { Application, SpectronClient } from 'spectron';
import { Guid } from '../../common/guid';
import {
  captureOnFailure,
  clearValue,
  createAccount,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  selectFromUserMenu,
  setupTest
} from './utils/common';

const retry = require('promise-retry');

async function dismissSuccessDialog(client: SpectronClient, message: string) {
  await client.waitForVisible('.message-dialog__title', METHOD_TIMEOUT);

  await expect(
    client.element('.message-dialog__message').getText()
  ).resolves.toMatch(message);

  await client.click('.message-dialog__buttons__confirm');
  await client.waitForVisible('.message-dialog__title', METHOD_TIMEOUT, true);
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
        await selectFromUserMenu(client, '.user-dropdown__accounting-settings');
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

  describe('crypto 2 crypto trades', () => {
    const message = 'Successfully set crypto to crypto consideration value';

    test('disable', async () => {
      await client
        .element(
          '.settings-accounting__crypto2crypto .v-input--selection-controls__input'
        )
        .click();
      await dismissSuccessDialog(client, message);
      await expect(
        client.getAttribute(
          '.settings-accounting__crypto2crypto input',
          'aria-checked'
        )
      ).resolves.toBe('false');
    });

    test('enable', async () => {
      await client
        .element(
          '.settings-accounting__crypto2crypto .v-input--selection-controls__input'
        )
        .click();
      await dismissSuccessDialog(client, message);
      await expect(
        client.getAttribute(
          '.settings-accounting__crypto2crypto input',
          'aria-checked'
        )
      ).resolves.toBe('true');
    });
  });

  describe('ethereum gas costs', () => {
    const message = 'Successfully set Ethereum gas costs value';

    test('disable', async () => {
      await client
        .element(
          '.settings-accounting__include-gas-costs .v-input--selection-controls__input'
        )
        .click();
      await dismissSuccessDialog(client, message);
      await expect(
        client.getAttribute(
          '.settings-accounting__include-gas-costs input',
          'aria-checked'
        )
      ).resolves.toBe('false');
    });

    test('enable', async () => {
      await client
        .element(
          '.settings-accounting__include-gas-costs .v-input--selection-controls__input'
        )
        .click();
      await dismissSuccessDialog(client, message);
      await expect(
        client.getAttribute(
          '.settings-accounting__include-gas-costs input',
          'aria-checked'
        )
      ).resolves.toBe('true');
    });
  });

  describe('tax free period', () => {
    const message = 'Successfully set trade settings';

    test('should by initially 365', async () => {
      await expect(
        client.getAttribute(
          '.settings-accounting__taxfree-period input',
          'aria-checked'
        )
      ).resolves.toBe('true');
      await expect(
        client.getValue('.settings-accounting__taxfree-period-days input')
      ).resolves.toEqual('365');
    });

    test('disable', async () => {
      await client
        .element(
          '.settings-accounting__taxfree-period .v-input--selection-controls__input'
        )
        .click();
      await expect(
        client.getAttribute(
          '.settings-accounting__taxfree-period input',
          'aria-checked'
        )
      ).resolves.toBe('false');
      await expect(
        client.getValue('.settings-accounting__taxfree-period-days input')
      ).resolves.toBe('');
    });

    test('save after disabling', async () => {
      await client.click('.settings-accounting__modify-trade-settings');
      await dismissSuccessDialog(client, message);
    });

    test('enable', async () => {
      await client
        .element(
          '.settings-accounting__taxfree-period .v-input--selection-controls__input'
        )
        .click();
      await expect(
        client.getAttribute(
          '.settings-accounting__include-gas-costs input',
          'aria-checked'
        )
      ).resolves.toBe('true');
    });

    test('set period', async () => {
      await clearValue(
        client,
        '.settings-accounting__taxfree-period-days input'
      );
      await client.addValue(
        '.settings-accounting__taxfree-period-days input',
        '150'
      );

      await expect(
        client.getValue('.settings-accounting__taxfree-period-days input')
      ).resolves.toEqual('150');
    });

    test('save after enabling', async () => {
      await client.click('.settings-accounting__modify-trade-settings');
      await dismissSuccessDialog(client, message);
    });
  });

  describe('ignored assets', () => {
    test('should initially have no ignored assets', async () => {
      await expect(
        client.getText('.settings-accounting__ignored-assets__badge')
      ).resolves.toMatch('0');
      await expect(
        client
          .element('.settings-accounting__buttons__add')
          .getAttribute('disabled')
      ).resolves.toBe('true');
      await expect(
        client
          .element('.settings-accounting__buttons__remove')
          .getAttribute('disabled')
      ).resolves.toBe('true');
    });

    test('ignoring assets should update the badge', async () => {
      await addIgnoredAsset(client, 'BSV');
      await expect(
        client.getText('.settings-accounting__ignored-assets__badge')
      ).resolves.toMatch('1');

      await addIgnoredAsset(client, 'GNT');
      await expect(
        client.getText('.settings-accounting__ignored-assets__badge')
      ).resolves.toMatch('2');
    });

    test('removing ignored assets should update the badge', async () => {
      await removeIgnoredAsset(client, 'BSV');
      await expect(
        client.getText('.settings-accounting__ignored-assets__badge')
      ).resolves.toMatch('1');

      await removeIgnoredAsset(client, 'GNT');
      await expect(
        client.getText('.settings-accounting__ignored-assets__badge')
      ).resolves.toMatch('0');
    });
  });
});

async function removeIgnoredAsset(client: SpectronClient, asset: string) {
  await client.element('.settings-accounting__ignored-assets').click();
  await client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
  await client.element(`.v-list-item__title=${asset}`).click();
  await client.waitForVisible('.v-select-list', METHOD_TIMEOUT, true);
  await client.click('.settings-accounting__buttons__remove');
}

async function addIgnoredAsset(client: SpectronClient, asset: string) {
  await clearValue(client, '.settings-accounting__asset input');
  await client.scroll('.settings-accounting__asset input');
  await client.addValue('.settings-accounting__asset input', asset);
  await expect(
    client.getValue('.settings-accounting__asset input')
  ).resolves.toEqual(asset);

  await client.click('.settings-accounting__buttons__add');
}
