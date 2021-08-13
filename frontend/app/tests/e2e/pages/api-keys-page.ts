export class ApiKeysPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__settings__api-keys').click({ force: true });
  }

  addExchange(
    apiKey: string,
    apiSecret: string,
    exchange: string,
    name: string
  ) {
    cy.get('.tab-navigation__tabs .settings__api-keys__exchanges').click({
      force: true
    });
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
    cy.get('[data-cy="bottom-dialog"]').find('[data-cy="confirm"]').click();
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
      .find('.location-display')
      .find('span')
      .eq(1)
      .should('contain', exchange);
    cy.get('@row').find('td').eq(1).should('contain', name);
  }
}
