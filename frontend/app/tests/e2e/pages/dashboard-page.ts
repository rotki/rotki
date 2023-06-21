import { type BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { RotkiApp } from './rotki-app';

export class DashboardPage {
  visit() {
    RotkiApp.navigateTo('dashboard');
  }

  getSanitizedAmountString(amount: string) {
    // TODO: extract the `replace(/,/g, '')` as to use user settings (when implemented)
    return amount.replace(/,/g, '');
  }

  getOverallBalance() {
    let overallBalance: BigNumber = Zero;
    return cy
      .get('.overall-balances__net-worth [data-cy="display-amount"]')
      .then($amount => {
        overallBalance = bigNumberify(
          this.getSanitizedAmountString($amount.text())
        );
        return overallBalance;
      });
  }

  getBlockchainBalances() {
    cy.get('.dashboard__summary-card__blockchain').should('be.visible');
    cy.get('[data-cy=blockchain-balances]').should('not.be.empty');
    const blockchainBalances = [
      { blockchain: 'Ethereum', symbol: Blockchain.ETH, value: Zero },
      { blockchain: 'Bitcoin', symbol: Blockchain.BTC, value: Zero }
    ];

    blockchainBalances.forEach(blockchainBalance => {
      const rowClass = `.dashboard__summary-card__blockchain [data-cy="blockchain-balance-box__item__${blockchainBalance.blockchain}"]`;
      cy.get('body').then($body => {
        if ($body.find(rowClass).length > 0) {
          cy.get(`${rowClass} [data-cy="display-amount"]`).each($amount => {
            blockchainBalance.value = blockchainBalance.value.plus(
              bigNumberify(this.getSanitizedAmountString($amount.text()))
            );
          });
        }
      });
    });

    return cy.wrap(blockchainBalances);
  }

  getNonFungibleBalances() {
    return cy.get('body').then($body => {
      const item =
        '[data-cy="nft-balance-table"] tbody tr:last-child td:nth-child(2) [data-cy="display-amount"]';
      const ntfTableExists = $body.find(item).length > 0;
      cy.log('NFT table exists', ntfTableExists);
      if (ntfTableExists) {
        return cy.get(item).then($amount => {
          if ($amount.length > 0) {
            return bigNumberify(this.getSanitizedAmountString($amount.text()));
          }
          return Zero;
        });
      }
      return cy.wrap(Zero);
    });
  }

  getLocationBalances() {
    cy.get('.dashboard__summary-card__manual').should('be.visible');
    cy.get('[data-cy=manual-balances]').should('not.be.empty');
    const balanceLocations = [
      { location: 'blockchain', value: Zero },
      { location: 'banks', value: Zero },
      { location: 'external', value: Zero },
      { location: 'commodities', value: Zero },
      { location: 'real estate', value: Zero },
      { location: 'equities', value: Zero }
    ];

    balanceLocations.forEach(balanceLocation => {
      const rowClass = `.dashboard__summary-card__manual [data-cy="manual-balance-box__item__${balanceLocation.location}"]`;
      cy.get('body').then($body => {
        if ($body.find(rowClass).length > 0) {
          cy.get(`${rowClass} [data-cy="display-amount"]`).each($amount => {
            balanceLocation.value = balanceLocation.value.plus(
              bigNumberify(this.getSanitizedAmountString($amount.text()))
            );
          });
        }
      });
    });

    return cy.wrap(balanceLocations);
  }

  amountDisplayIsBlurred() {
    cy.get('[data-cy="display-wrapper"]').should($div => {
      expect($div.css('filter')).to.match(/^blur/);
    });
  }

  amountDisplayIsNotBlurred() {
    cy.get('[data-cy="display-wrapper"]').should($div => {
      expect($div.css('filter')).not.to.match(/^blur/);
    });
  }

  percentageDisplayIsBlurred() {
    cy.get('.percentage-display__amount').should('have.class', 'blur-content');
  }

  percentageDisplayIsNotBlurred() {
    cy.get('.percentage-display__amount').should(
      'not.have.class',
      'blur-content'
    );
  }
}
