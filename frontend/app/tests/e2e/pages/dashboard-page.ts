import { default as BigNumber } from 'bignumber.js';
import { bigNumberify, Zero } from '../../../src/utils/bignumbers';

export class DashboardPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__dashboard').click();
  }

  getOverallBalance() {
    let overallBalance: BigNumber = Zero;
    const balance = cy
      .get('.overall-balances-box .amount-display__value')
      .then($amount => {
        overallBalance = bigNumberify($amount.text().replace(',', ''));
        return overallBalance;
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
                      $amount.text().replace(',', '')
                    );
                  } else {
                    balanceLocation.renderedValue = balanceLocation.renderedValue.plus(
                      bigNumberify($amount.text().replace(',', ''))
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
}
