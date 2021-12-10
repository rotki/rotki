import { BigNumber } from '@rotki/common';
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
      .get('.overall-balances__net-worth .amount-display__value')
      .then($amount => {
        overallBalance = bigNumberify(
          this.getSanitizedAmountString($amount.text())
        );
        return overallBalance;
      });

    return balance;
  }

  getBlockchainBalances() {
    const blockchainBalances = [
      { blockchain: 'Ethereum', renderedValue: Zero },
      { blockchain: 'Bitcoin', renderedValue: Zero }
    ];

    blockchainBalances.forEach(blockchainBalance => {
      cy.get('[data-cy="blockchain-balance-box__item"]').then($rows => {
        if ($rows.text().includes(blockchainBalance.blockchain)) {
          cy.get(
            `[data-cy="blockchain-balance-box__item"]:contains(${blockchainBalance.blockchain})`
          ).each($row => {
            // loops over all blockchain asset balances rows and adds up the total per blockchain type
            cy.wrap($row)
              .find('.amount-display__value')
              .then($amount => {
                if (blockchainBalance.renderedValue === Zero) {
                  blockchainBalance.renderedValue = bigNumberify(
                    this.getSanitizedAmountString($amount.text())
                  );
                } else {
                  blockchainBalance.renderedValue =
                    blockchainBalance.renderedValue.plus(
                      this.getSanitizedAmountString($amount.text())
                    );
                }
              });
          });
        }
      });
    });

    return cy.wrap(blockchainBalances);
  }

  getNonFungibleBalances() {
    const balance = cy
      .get(
        '[data-cy="nft-balance-table"] tbody tr:last-child td:nth-child(2) > .amount-display > .v-skeleton-loader .amount-display__value'
      )
      .then($amount => {
        if ($amount.length > 0) {
          return bigNumberify(this.getSanitizedAmountString($amount.text()));
        }
        return Zero;
      });

    return balance;
  }

  getLocationBalances() {
    const balanceLocations = [
      { location: 'Blockchain', renderedValue: Zero },
      { location: 'Banks', renderedValue: Zero },
      { location: 'External', renderedValue: Zero },
      { location: 'Commodities', renderedValue: Zero },
      { location: 'Real estate', renderedValue: Zero },
      { location: 'Equities', renderedValue: Zero }
    ];

    balanceLocations.forEach(balanceLocation => {
      cy.get('.dashboard__summary-card__manual .manual-balance-box__item').then(
        $rows => {
          if ($rows.text().includes(balanceLocation.location)) {
            cy.get(
              `.dashboard__summary-card__manual .manual-balance-box__item:contains(${balanceLocation.location})`
            ).each($row => {
              // loops over all manual balances rows and adds up the total per location
              // TODO: extract the replace(',', '') as to use user settings (when implemented)
              cy.wrap($row)
                .find('.amount-display__value')
                .then($amount => {
                  if (balanceLocation.renderedValue === Zero) {
                    balanceLocation.renderedValue = bigNumberify(
                      this.getSanitizedAmountString($amount.text())
                    );
                  } else {
                    balanceLocation.renderedValue =
                      balanceLocation.renderedValue.plus(
                        bigNumberify(
                          this.getSanitizedAmountString($amount.text())
                        )
                      );
                  }
                });
            });
          }
        }
      );
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
