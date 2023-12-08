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
      url: '/#/user/login',
      qs: {
        skip_update: '1'
      }
    });
  }

  createAccount(username: string, password = '1234') {
    cy.logout();
    cy.visit({
      url: '/#/user/create',
      qs: {
        skip_update: '1'
      },
      timeout: 10000
    });
    cy.get('[data-cy=connection-loading__content]').should('not.exist');
    cy.get('[data-cy=account-management-forms]').scrollIntoView();
    cy.get('[data-cy=account-management-forms]').should('be.visible');

    cy.get('[data-cy="create-account__introduction__continue"]').click();
    cy.get('[data-cy="create-account__premium__button__continue"]').click();
    cy.get('[data-cy="create-account__fields__username"]').type(username);
    cy.get('[data-cy="create-account__fields__password"]').type(password);
    cy.get('[data-cy="create-account__fields__password-repeat"]').type(
      password
    );
    cy.get('[data-cy="create-account__boxes__user-prompted"] > label').click();
    cy.get('[data-cy="create-account__credentials__button__continue"]').click();
    cy.get(
      '[data-cy="create-account__submit-analytics__button__continue"]'
    ).click();
    cy.get('[data-cy=account-management-forms]').should('not.exist');
    cy.updateAssets();
    this.loadEnv();
  }

  clear() {
    cy.logout();
    cy.visit('/');
  }

  fasterLogin(username: string, password = '1234', disableModules = false) {
    cy.logout();
    cy.createAccount(username, password);
    if (disableModules) {
      cy.disableModules();
    }
    this.loadEnv();
    cy.visit({
      url: '/',
      qs: {
        skip_update: '1'
      }
    });
    this.login(username, password);
  }

  checkGetPremiumButton() {
    cy.get('[data-cy=get-premium-button]').should('be.visible');
  }

  relogin(username: string, password = '1234'): void {
    cy.logout();
    cy.visit('/#/user/login');
    this.login(username, password);
  }

  login(username: string, password = '1234') {
    cy.get('[data-cy=username-input] input').should('be.visible');
    cy.get('[data-cy=username-input] input').as('username');
    cy.get('[data-cy=password-input] input').as('password');
    cy.get('@username').clear();
    cy.get('@username').should('be.empty');
    cy.get('@username').type(username);
    cy.get('@username').should('have.value', username);
    cy.get('@password').clear();
    cy.get('@username').should('be.empty');
    cy.get('@password').type(password);
    cy.get('@password').should('have.value', password);
    cy.get('[data-cy=login-submit]').click();
  }

  logout() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__logout').click();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    cy.get('[data-cy=username-input] input').should('be.visible');
  }

  changeCurrency(currency: string) {
    cy.get('.currency-dropdown').click();
    cy.get(`#change-to-${currency.toLocaleLowerCase()}`).click();
  }

  togglePrivacyMenu(show?: boolean) {
    cy.get('[data-cy=privacy-menu]').as('menu');
    if (show) {
      cy.get('@menu').click();
      cy.get('[data-cy="privacy-mode-scramble__toggle"]');
    } else {
      cy.get('@menu').click({ force: true });
    }
  }

  changePrivacyMode(mode: number) {
    this.togglePrivacyMenu(true);
    cy.get(
      '[data-cy="privacy-mode-dropdown__input"] ~ .v-slider__thumb-container'
    ).as('input');

    cy.get('@input').focus();
    cy.get('@input').type('{downArrow}'.repeat(2));

    if (mode > 0) {
      cy.get('@input').type('{upArrow}'.repeat(mode));
    }
    this.togglePrivacyMenu();
  }

  toggleScrambler(enable: boolean) {
    cy.get(
      '[data-cy="privacy-mode-scramble__toggle"] input[type="checkbox"]'
    ).as('input');

    if (enable) {
      cy.get('@input').check();
    } else {
      cy.get('@input').uncheck();
    }
  }

  changeScrambleValue(multiplier: string) {
    this.toggleScrambler(true);
    cy.get('[data-cy="privacy-mode-scramble__multiplier"]').as('input');

    cy.get('@input').type(multiplier);
  }

  changeRandomScrambleValue() {
    this.toggleScrambler(true);
    cy.get('[data-cy="privacy-mode-scramble__multiplier"]').as('input');
    cy.get('[data-cy="privacy-mode-scramble__random-multiplier"]').as('button');

    cy.get('@button').click();
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
