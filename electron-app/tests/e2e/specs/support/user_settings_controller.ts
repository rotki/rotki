import { SpectronClient } from 'spectron';
import { METHOD_TIMEOUT } from '../utils/common';
const retry = require('promise-retry');
export enum AccountType {
  ETH = 'ETH',
  BTC = 'BTC'
}

export class UserSettingsController {
  constructor(private client: SpectronClient) {}

  async addFiatValue(amount: number = 50) {
    await this.client.scroll('.fiat-balances__currency', 0, 0);
    await this.client.click('.fiat-balances__currency');
    await this.client.element('.fiat-balances__currency').click('option=USD');
    await this.client.addValue('.fiat-balances__balance', amount);
    await retry(async () => {
      this.client.click('.fiat-balances__action');
    });
  }

  async addAccount(accountType: AccountType, account: string) {
    await this.clearAccountInput();
    await retry(async () => {
      this.client.scroll('.blockchain-balances__chain', 0, 0);
      this.client.click('.blockchain-balances__chain');
      this.client
        .element('.blockchain-balances__chain')
        .click(`option=${accountType}`);
    });

    await this.client.addValue('.blockchain-balances__address', account);
    await this.client.click('.blockchain-balances__buttons__add');
  }

  async clearAccountInput() {
    await this.client.waitForEnabled(
      '.blockchain-balances__address',
      METHOD_TIMEOUT
    );
    await this.client.waitForEnabled(
      '.blockchain-balances__chain',
      METHOD_TIMEOUT
    );
    await this.client.waitForEnabled(
      '.blockchain-balances__buttons__add',
      METHOD_TIMEOUT
    );
    await this.client.clearElement('.blockchain-balances__address');
  }

  async addExchange(apiKey: string, apiSecret: string) {
    await this.client.scroll('#setup_exchange', 0, 0);
    await retry(async () => {
      this.client.click('#setup_exchange');
    });
    await this.client.element('#setup_exchange').click('option=bittrex');

    await this.client.addValue('#api_key_entry', apiKey);
    await this.client.addValue('#api_secret_entry', apiSecret);

    await retry(async () => {
      this.client.click('#setup_exchange_button');
    });

    await this.client.waitForExist('#bittrex_badge', METHOD_TIMEOUT);
  }
}
