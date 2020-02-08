import { Application, SpectronClient } from 'spectron';
import {
  captureOnFailure,
  createAccount,
  dismissSuccessDialog,
  GLOBAL_TIMEOUT,
  initSpectron,
  METHOD_TIMEOUT,
  navigateTo,
  selectOption,
  setupTest,
  setValue
} from './utils/common';
import { Guid } from './utils/guid';
import moment from 'moment';

const retry = require('promise-retry');

jest.setTimeout(GLOBAL_TIMEOUT);

describe('otc trades', () => {
  let application: Application;
  let stop: () => Promise<Application>;
  let client: SpectronClient;

  let username: string;
  const password: string = process.env.PASSWORD as string;

  beforeAll(async () => {
    username = Guid.newGuid().toString();
    ({ application, stop } = await initSpectron());
    ({ client } = application);

    await setupTest(application, 'otc trades', async () => {
      await createAccount(application, username, password);

      await navigateTo(client, '.navigation__otc-trades');
      await client.waitUntilTextExists('h1', 'OTC Trades List', METHOD_TIMEOUT);
    });
  });

  afterAll(async () => {
    await stop();
  });

  afterEach(async () => {
    await captureOnFailure(application);
  });

  describe('adding external trades', () => {
    const trade = {
      timestamp: 1439196535,
      pair: 'BTC_EUR',
      rate: '268.678317859',
      fee: '0',
      fee_currency: 'BTC',
      amount: '82',
      link: '',
      location: 'external',
      notes: '',
      trade_type: 'sell'
    };

    test('set date', async () => {
      await setValue(
        client,
        '.otc-form__date input',
        moment(trade.timestamp * 1000).format('DD/MM/YYYY HH:mm')
      );
    });

    test('set pair', async () => {
      await setValue(client, '.otc-form__pair input', trade.pair);
    });

    test('set type', async () => {
      await selectOption(client, '.otc-form__type input', trade.trade_type);
    });

    test('set amount', async () => {
      await setValue(client, '.otc-form__amount input', trade.amount);
    });

    test('set rate', async () => {
      await setValue(client, '.otc-form__rate input', trade.rate);
    });

    test('set fee', async () => {
      await setValue(client, '.otc-form__fee input', trade.fee);
    });

    test('set fee currency', async () => {
      await setValue(
        client,
        '.otc-form__fee-currency input',
        trade.fee_currency
      );
    });

    test('save', async () => {
      await retry(async () => {
        await client.click('.otc-form__buttons__save');
      });
    });

    test('dismiss dialog', async () => {
      await dismissSuccessDialog(client, 'Trade was submitted successfully');
    });

    test('add second trade', async () => {
      const trade = {
        timestamp: 1439196535,
        pair: 'ETH_EUR',
        rate: '0.2315893',
        fee: '0',
        fee_currency: 'ETH',
        amount: '1450',
        link: '',
        location: 'external',
        notes: '',
        trade_type: 'sell'
      };
      await setValue(
        client,
        '.otc-form__date input',
        moment(trade.timestamp * 1000).format('DD/MM/YYYY HH:mm')
      );
      await setValue(client, '.otc-form__pair input', trade.pair);
      await selectOption(client, '.otc-form__type input', trade.trade_type);
      await setValue(client, '.otc-form__amount input', trade.amount);
      await setValue(client, '.otc-form__rate input', trade.rate);
      await setValue(client, '.otc-form__fee input', trade.fee);
      await setValue(
        client,
        '.otc-form__fee-currency input',
        trade.fee_currency
      );

      await retry(async () => {
        await client.click('.otc-form__buttons__save');
      });

      await dismissSuccessDialog(client, 'Trade was submitted successfully');
    });

    test('two trades are displayed', async () => {
      const matchedElements = (
        await client.elements('.otc-trades__data tbody > tr')
      ).value;

      expect(matchedElements.length).toEqual(2);
    });

    test('the trade should display properly', async () => {
      await expect(
        client.getText(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(1)'
        )
      ).resolves.toContain('BTC_EUR');
      await expect(
        client.getText(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(3)'
        )
      ).resolves.toContain('82');
      await expect(
        client.getText(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(4)'
        )
      ).resolves.toContain('268.678317859');
      await expect(
        client.getText(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(5)'
        )
      ).resolves.toMatch('10/08/2015 10:48');
    });
  });

  describe('managing external trades', () => {
    test('editing a trade', async () => {
      await client
        .element(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(6) > .v-icon'
        )
        .click();

      await setValue(client, '.otc-form__amount input', '120');
      await client.click('.otc-trades__buttons_save');
      await dismissSuccessDialog(client, 'Trade was submitted successfully');

      await expect(
        client.getText(
          '.otc-trades__data tbody > tr:nth-child(1) > td:nth-child(3)'
        )
      ).resolves.toContain('120');
    });

    test('deleting a trade', async () => {
      await client
        .element('.otc-trades__data tbody > tr:nth-child(1)')
        .rightClick();
      await client.click('.context-menu-list > li:nth-child(2)');

      await dismissSuccessDialog(client, '');

      const matchedElements = (
        await client.elements('.otc-trades__data tbody > tr')
      ).value;

      await expect(matchedElements.length).resolves.toEqual(1);
    });
  });
});
