import { mockRequest } from '../support/utils';
import { RotkiApp } from './rotki-app';

export class ApiKeysPage {
  visit(submenu: string) {
    RotkiApp.navigateTo('api-keys', submenu);
  }

  addExchange(
    apiKey: string,
    apiSecret: string,
    exchange: string,
    name: string
  ) {
    cy.get('[data-cy="exchanges"]').find('[data-cy="add-exchange"]').click();
    cy.get('[data-cy="exchange-keys"]').as('keys');
    cy.get('[data-cy="bottom-dialog"]', { timeout: 45000 }).should(
      'be.visible'
    );
    cy.get('@keys')
      .find('[data-cy="exchange"]')
      .type(`{selectall}{backspace}${exchange}{enter}`);

    cy.get('@keys').find('[data-cy="name"]').type(name);
    cy.get('@keys').find('[data-cy="api-key"] input').type(apiKey);
    cy.get('@keys').find('[data-cy="api-secret"] input').type(apiSecret);

    cy.intercept(
      {
        url: '/api/1/exchanges',
        method: 'PUT'
      },
      {
        statusCode: 200,
        body: {
          result: true
        }
      }
    ).as('exchangeAdd');

    const waitForBalances = mockRequest({
      url: `/api/1/exchanges/balances/${exchange}?async_query=true`,
      method: 'GET'
    });

    cy.get('[data-cy="bottom-dialog"]').find('[data-cy="confirm"]').click();
    waitForBalances();
    cy.wait('@exchangeAdd', { timeout: 30000 });

    cy.get('[data-cy="bottom-dialog"]', { timeout: 45000 }).should(
      'not.be.visible'
    );
  }

  exchangeIsAdded(exchange: string, name: string) {
    cy.get('[data-cy="exchange-table"]').find('table').as('table');

    cy.get('@table').find('tr').eq(1).as('row');
    cy.get('@row')
      .find('td')
      .eq(0)
      .find('[data-cy=location-icon]')
      .find('span')
      .should('contain', exchange);
    cy.get('@row').find('td').eq(1).should('contain', name);
  }
}
