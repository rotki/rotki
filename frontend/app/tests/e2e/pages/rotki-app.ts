export class RotkiApp {
  visit() {
    cy.visit('/?skip_update=1');
  }

  createAccount(username: string, password: string = '1234') {
    cy.logout();
    // simulate high scaling / low res by making a very small viewpoirt
    cy.get('.login__button__new-account').click();
    cy.get('.create-account__fields__username').type(username);
    cy.get('.create-account__fields__password').type(password);
    cy.get('.create-account__fields__password-repeat').type(password);
    cy.get('.create-account__boxes__user-prompted').click();
    cy.get('.create-account__buttons__continue').click();
    cy.get('.create-account__analytics__buttons__confirm').click();
    cy.updateAssets();
  }

  closePremiumOverlay() {
    cy.get('.premium-reminder__title', {
      timeout: 10000
    }).should('include.text', 'Upgrade to Premium');
    cy.get('.premium-reminder__buttons__cancel').click();
    cy.get('.premium-reminder').should('not.be.visible');
  }

  login(username: string, password: string = '1234') {
    cy.get('.login__fields__username').type(username);
    cy.get('.login__fields__password').type(password);
    cy.get('.login__button__sign-in').click();
  }

  logout() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__logout').click();
    cy.get('.confirm-dialog__buttons__confirm').filter(':visible').click();
    cy.get('.login__fields__username').should('be.visible');
  }

  changeCurrency(currency: string) {
    cy.get('.currency-dropdown').click();
    cy.get(`#change-to-${currency.toLocaleLowerCase()}`).click();
  }

  togglePrivacyMode() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__privacy-mode').click();
  }

  drawerIsVisible(isVisible: boolean) {
    cy.get('.account-management__loading').should('not.be.visible');
    cy.get('.app__navigation-drawer').should(
      isVisible ? 'be.visible' : 'not.be.visible'
    );
  }
}
