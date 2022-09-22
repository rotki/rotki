export class RotkiApp {
  private loadEnv(): void {
    const apiKey = Cypress.env('ETHERSCAN_API_KEY');
    if (apiKey) {
      cy.log('Using CYPRESS_ETHERSCAN_API_KEY env variable');
      cy.addEtherscanKey(apiKey);
    } else {
      cy.log('CYPRESS_ETHERSCAN_API_KEY not set');
    }
  }

  visit() {
    cy.visit('/?skip_update=1');
  }

  createAccount(username: string, password: string = '1234') {
    cy.logout();
    // simulate high scaling / low res by making a very small viewport
    cy.get('.connection-loading__content').should('not.exist');
    cy.get('[data-cy=account-management-forms]').should('be.visible');

    cy.get('[data-cy=account-management]').then($body => {
      const button = $body.find('[data-cy=new-account]');
      if (button.length > 0) {
        cy.get('[data-cy=new-account]').scrollIntoView().click();
      }
    });

    cy.get('[data-cy="create-account__premium__button__continue"]').click();
    cy.get('.create-account__fields__username').type(username);
    cy.get('.create-account__fields__password').type(password);
    cy.get('.create-account__fields__password-repeat').type(password);
    cy.get('.create-account__boxes__user-prompted').click();
    cy.get('.create-account__credentials__button__continue').click();
    cy.get('.create-account__analytics__button__confirm').click();
    cy.get('[data-cy=account-management__loading]').should('not.exist');
    cy.updateAssets();
    this.loadEnv();
  }

  fasterLogin(
    username: string,
    password: string = '1234',
    disableModules: boolean = false
  ) {
    cy.createAccount(username, password);
    if (disableModules) {
      cy.disableModules();
    }
    this.loadEnv();
    this.visit();
    this.login(username, password);
    this.closePremiumOverlay();
  }

  fasterLogout() {
    cy.logout();
    this.visit();
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
    cy.get('[data-cy=privacy-menu]').click();
    cy.get(
      '[data-cy="privacy-mode-dropdown__input"] ~ .v-slider__thumb-container'
    ).as('input');

    cy.get('@input').focus().type('{downarrow}'.repeat(2));

    if (mode > 0) {
      cy.get('@input').type('{uparrow}'.repeat(mode));
    }
    cy.get('[data-cy=privacy-menu]').click();
  }

  drawerIsVisible(isVisible: boolean) {
    cy.get('.app__navigation-drawer').should(
      isVisible ? 'be.visible' : 'not.be.visible'
    );
  }
}
