import { type BigNumber } from '@rotki/common';
import { Zero } from '@/utils/bignumbers';
import { parseBigNumber, updateLocationBalance } from '../utils/amounts';
import { RotkiApp } from './rotki-app';

export class DashboardPage {
  visit() {
    RotkiApp.navigateTo('dashboard');
  }

  getOverallBalance() {
    return cy
      .get('[data-cy="overall-balances__net-worth"] [data-cy="display-amount"]')
      .then($amount => parseBigNumber($amount.text()));
  }

  getBlockchainBalances() {
    cy.get('[data-cy=blockchain-balances]').should('be.visible');
    cy.get('[data-cy=blockchain-balances]').should('not.be.empty');

    const balances: Map<string, BigNumber> = new Map<string, BigNumber>();

    cy.get('[data-cy=blockchain-balance__summary').each($element => {
      const location = $element.attr('data-location');
      if (!location) {
        cy.log('missing location for element ', $element);
        return true;
      }

      const amount = $element.find('[data-cy="display-amount"]').text();
      updateLocationBalance(amount, balances, location);
    });
    return cy.wrap(balances);
  }

  getNonFungibleBalances() {
    return cy.get('[data-cy=dashboard]').then($dashboard => {
      const nftTable = $dashboard.find('[data-cy="nft-balance-table"]');
      const nftTableExists = nftTable.length > 0;

      cy.log('NFT table exists', nftTableExists);

      if (!nftTableExists) {
        return cy.wrap(Zero);
      }
      const selector =
        'tbody tr:last-child td:nth-child(2) [data-cy="display-amount"]';
      const $displayAmount = nftTable.find(selector);

      let amount = Zero;
      if ($displayAmount.length > 0) {
        amount = parseBigNumber($displayAmount.text());
      }
      return cy.wrap(amount);
    });
  }

  getLocationBalances() {
    cy.get('[data-cy=manual-balances]').as('manual_balances');
    cy.get('@manual_balances').should('be.visible');
    cy.get('@manual_balances').should('not.be.empty');

    const balances: Map<string, BigNumber> = new Map();

    cy.get('[data-cy=manual-balance__summary').each($element => {
      const location = $element.attr('data-location');
      if (!location) {
        cy.log('missing location for element ', $element);
        return true;
      }

      const amount = $element.find('[data-cy="display-amount"]').text();
      updateLocationBalance(amount, balances, location);
    });

    return cy.wrap(balances);
  }

  amountDisplayIsBlurred() {
    cy.get('[data-cy="amount-display"]').should($div => {
      expect($div.css('filter')).to.match(/^blur/);
    });
  }

  amountDisplayIsNotBlurred() {
    cy.get('[data-cy="amount-display"]').should($div => {
      expect($div.css('filter')).not.to.match(/^blur/);
    });
  }

  percentageDisplayIsBlurred() {
    cy.get('.percentage-display__amount').should('have.class', 'blur');
  }

  percentageDisplayIsNotBlurred() {
    cy.get('.percentage-display__amount').should('not.have.class', 'blur');
  }
}
