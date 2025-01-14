import { RotkiApp } from '../rotki-app';
import { parseBigNumber } from '../../utils/amounts';

export class BlockchainBalancesPage {
  visit() {
    RotkiApp.navigateTo('balances', 'balances-blockchain');
    cy.assertNoRunningTasks();
  }

  getTotals() {
    this.visit();
    return cy.get('[data-cy=blockchain-asset-balances]')
      .find('tbody')
      .find('tr:last-child td:nth-child(2)')
      .find('[data-cy=display-amount]')
      .invoke('text')
      .then(text => parseBigNumber(text));
  }
}
