import { TK } from '../common/tk';

export class RotkiApp {
  private loadEnv(): void {
    const apiKey = Cypress.env('ETHERSCAN_API_KEY') ?? TK.join('');
    if (apiKey) {
      cy.log('Using CYPRESS_ETHERSCAN_API_KEY env variable');
      cy.addEtherscanKey(apiKey);
    } else {
      cy.log('CYPRESS_ETHERSCAN_API_KEY not set');
    }
  }

  visit() {
    cy.visit({
      url: '/',
      qs: {
        skip_update: '1'
      }
    });
  }

  createAccount(username: string, password = '1234') {
    cy.logout();
    // simulate high scaling / low res by making a very small viewport
    cy.get('.connection-loading__content').should('not.exist');
    cy.get('[data-cy=account-management-forms]').scrollIntoView();
    cy.get('[data-cy=account-management-forms]').should('be.visible');

    cy.get('[data-cy=account-management]').then($body => {
      const button = $body.find('[data-cy=new-account]');
      if (button.length > 0) {
        cy.get('[data-cy=new-account]').scrollIntoView();
        cy.get('[data-cy=new-account]').click();
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

  fasterLogin(username: string, password = '1234', disableModules = false) {
    cy.createAccount(username, password);
    if (disableModules) {
      cy.disableModules();
    }
    this.loadEnv();
    this.visit();
    this.login(username, password);
  }

  fasterLogout() {
    cy.logout();
    this.visit();
  }

  checkGetPremiumButton() {
    cy.get('[data-cy=get-premium-button]').should('be.visible');
  }

  login(username: string, password = '1234') {
    cy.get('[data-cy=username-input]').should('be.visible');
    cy.get('[data-cy=username-input] input:not([type=hidden])').as('username');
    cy.get('[data-cy=password-input] input:not([type=hidden])').as('password');
    cy.get('@username').clear();
    cy.get('@username').type(username);
    cy.get('@password').clear();
    cy.get('@password').type(password);
    cy.get('[data-cy=login-submit]').click();
  }

  logout() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__logout').click();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    cy.get('[data-cy=username-input]').should('be.visible');
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

    cy.get('@input').focus();
    cy.get('@input').type('{downArrow}'.repeat(2));

    if (mode > 0) {
      cy.get('@input').type('{upArrow}'.repeat(mode));
    }
    cy.get('[data-cy=privacy-menu]').click({ force: true });
  }

  /**
   * to get single query param values from route
   * @param {string} key
   * @param {string} value
   */
  shouldHaveQueryParam(key: string, value: string) {
    cy.location().should(loc => {
      const query = new URLSearchParams(loc.href);
      expect(query.get(key)).to.equal(value);
    });
  }

  /**
   * to get array query param values from route
   * @param {string} key
   * @param {string[]} values
   */
  shouldHaveQueryParams(key: string, values: string[]) {
    cy.location().should(loc => {
      const query = new URLSearchParams(loc.href);
      expect(query.getAll(key)).to.deep.equal(values);
    });
  }

  static navigateTo(menu: string, submenu?: string) {
    const click = (selector: string) => {
      cy.get(selector).scrollIntoView();
      cy.get(selector).should('be.visible');
      cy.get(selector).trigger('mouseover');
      cy.get(selector).click();
    };

    const menuClass = `.navigation__${menu}`;
    cy.get(menuClass).then(menu => {
      const parent = menu.parent().parent();
      if (!parent.hasClass('v-list-group--active')) {
        click(menuClass);
      }

      if (submenu) {
        cy.get(menuClass)
          .parent()
          .parent()
          .find('.v-list-group__items')
          .scrollIntoView();

        const subMenuClass = `.navigation__${submenu}`;
        click(subMenuClass);
      }
    });
  }
}
