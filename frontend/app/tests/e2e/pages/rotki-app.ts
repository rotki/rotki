export class RotkiApp {
  visit() {
    cy.visit('/?skip_update=1');
  }

  createAccount(username: string, password: string = '1234') {
    cy.logout();
    // simulate high scaling / low res by making a very small viewpoirt
    cy.get('.connection-loading__content').should('not.exist');
    cy.get('.account-management__card').then($body => {
      const button = $body.find('.login__button__new-account');
      if (button.length > 0) {
        cy.get('.login__button__new-account').click();
      }
    });

    cy.get('[data-cy="create-account__premium__button__continue"]').click();
    cy.get('.create-account__fields__username').type(username);
    cy.get('.create-account__fields__password').type(password);
    cy.get('.create-account__fields__password-repeat').type(password);
    cy.get('.create-account__boxes__user-prompted').click();
    cy.get('.create-account__credentials__button__continue').click();
    cy.get('.create-account__analytics__button__confirm').click();
    cy.get('.account-management__loading').should('not.exist');
    cy.updateAssets();
  }

  closePremiumOverlay() {
    cy.get('.premium-reminder__title', {
      timeout: 10000
    }).should('include.text', 'Upgrade to Premium');
    cy.get('.premium-reminder__buttons__cancel').click();
    cy.get('.premium-reminder').should('not.exist');
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
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    cy.get('.login__fields__username').should('be.visible');
  }

  changeCurrency(currency: string) {
    cy.get('.currency-dropdown').click();
    cy.get(`#change-to-${currency.toLocaleLowerCase()}`).click();
  }

  changePrivacyMode(mode: number) {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy="user-dropdown__privacy-mode"]').click();
    cy.get(
      '[data-cy="user-dropdown__privacy-mode__input"] ~ .v-slider__thumb-container'
    ).as('input');

    cy.get('@input').focus().type('{downarrow}'.repeat(3));

    if (mode > 0) {
      cy.get('@input').type('{uparrow}'.repeat(mode));
    }
    cy.get('[data-cy="user-dropdown__privacy-mode"]').click();
    cy.get('.user-dropdown').click();
  }

  drawerIsVisible(isVisible: boolean) {
    cy.get('.app__navigation-drawer').should(
      isVisible ? 'be.visible' : 'not.be.visible'
    );
  }
}
