export class ApiKeysPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__api-keys').click();
  }

  addExchange(apiKey: string, apiSecret: string, exchange: string) {
    cy.get('.exchange-settings__fields__exchange').click();
    cy.get(`.exchange__${exchange}`).click();
    cy.get('.exchange-settings__fields__api-key').type(apiKey);
    cy.get('.exchange-settings__fields__api-secret').type(apiSecret);
  }
}
