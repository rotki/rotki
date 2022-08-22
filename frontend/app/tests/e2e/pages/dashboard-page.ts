import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { bigNumberify, Zero } from '@/utils/bignumbers';

export class DashboardPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__dashboard').click();
  }

  getSanitizedAmountString(amount: string) {
    // TODO: extract the `replace(/,/g, '')` as to use user settings (when implemented)
    return amount.replace(/,/g, '');
  }

  getOverallBalance() {
    let overallBalance: BigNumber = Zero;
    const balance = cy
      .get('.overall-balances__net-worth [data-cy="display-amount"]')
      .then($amount => {
        overallBalance = bigNumberify(
          this.getSanitizedAmountString($amount.text())
        );
        return overallBalance;
      });

    return balance;
  }

  getBlockchainBalances() {
    cy.get('.dashboard__summary-card__blockchain').should('be.visible');
    cy.get('[data-cy=blockchain-balances]').should('not.be.empty');
    const blockchainBalances = [
      { blockchain: 'Ethereum', symbol: Blockchain.ETH, renderedValue: Zero },
      { blockchain: 'Bitcoin', symbol: Blockchain.BTC, renderedValue: Zero }
    ];

    blockchainBalances.forEach(blockchainBalance => {
      const rowClass = `.dashboard__summary-card__blockchain [data-cy="blockchain-balance-box__item__${blockchainBalance.blockchain}"]`;
      cy.get('body').then($body => {
        if ($body.find(rowClass).length > 0) {
          cy.get(`${rowClass} [data-cy="display-amount"]`).each($amount => {
            blockchainBalance.renderedValue =
              blockchainBalance.renderedValue.plus(
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
      { location: 'blockchain', renderedValue: Zero },
      { location: 'banks', renderedValue: Zero },
      { location: 'external', renderedValue: Zero },
      { location: 'commodities', renderedValue: Zero },
      { location: 'real estate', renderedValue: Zero },
      { location: 'equities', renderedValue: Zero }
    ];

    balanceLocations.forEach(balanceLocation => {
      const rowClass = `.dashboard__summary-card__manual [data-cy="manual-balance-box__item__${balanceLocation.location}"]`;
      cy.get('body').then($body => {
        if ($body.find(rowClass).length > 0) {
          cy.get(`${rowClass} [data-cy="display-amount"]`).each($amount => {
            balanceLocation.renderedValue = balanceLocation.renderedValue.plus(
              bigNumberify(this.getSanitizedAmountString($amount.text()))
            );
          });
        }
      });
    });

    return cy.wrap(balanceLocations);
  }

  amountDisplayIsBlurred() {
    cy.get('.amount-display').should('have.class', 'blur-content');
  }

  amountDisplayIsNotBlurred() {
    cy.get('.amount-display').should('not.have.class', 'blur-content');
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
