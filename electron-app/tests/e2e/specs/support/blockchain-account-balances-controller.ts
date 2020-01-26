import { SpectronClient } from 'spectron';
import { METHOD_TIMEOUT } from '../utils/common';

export enum AccountType {
  ETH = 'ETH',
  BTC = 'BTC'
}

export class BlockchainAccountBalancesController {
  constructor(private client: SpectronClient) {}

  async addFiatValue(amount: number = 50) {
    await this.client.scroll('.fiat-balances', 0, 0);
    await this.client.waitUntil(
      () => this.client.element('.fiat-balances__currency').isEnabled(),
      METHOD_TIMEOUT
    );
    await this.client.click('.fiat-balances__currency');
    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
    this.client.element(`.v-list-item__title=USD`).click();
    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT, false);
    await this.client.addValue('.fiat-balances__balance input', amount);
    this.client.click('.fiat-balances__action-button');
  }

  async addAccount(accountType: AccountType, account: string) {
    this.client.scroll('.blockchain-balances', 0, 0);
    await this.client.waitUntil(
      () => this.client.element('.blockchain-balances__chain').isEnabled(),
      METHOD_TIMEOUT
    );
    this.client.element('.blockchain-balances__chain').click();
    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT);
    this.client.element(`.v-list-item__title=${accountType}`).click();
    await this.client.waitForVisible('.v-select-list', METHOD_TIMEOUT, false);

    await this.client.scroll(`.blockchain-balances__address`, 0, 0);
    await this.client.addValue(`.blockchain-balances__address input`, account);
    await this.client.click(`.blockchain-balances__buttons__add`);
  }
}
