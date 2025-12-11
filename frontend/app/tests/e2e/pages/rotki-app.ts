import { TK } from '../common/tk';

export class RotkiApp {
  private loadEnv(): void {
    const apiKey = Cypress.env('ETHERSCAN_API_KEY') ?? TK.join('');
    if (apiKey) {
      cy.log('Using CYPRESS_ETHERSCAN_API_KEY env variable');
      cy.addEtherscanKey(apiKey);
    }
    else {
      cy.log('CYPRESS_ETHERSCAN_API_KEY not set');
    }
  }

  visit() {
    cy.visit({
      url: '/#/user/login',
      qs: {
        skip_update: '1',
      },
    });
  }

  createAccount(username: string, password = '1234') {
    cy.logout();
    cy.visit({
      url: '/#/user/create',
      qs: {
        skip_update: '1',
      },
      timeout: 10000,
    });
    cy.get('[data-cy=connection-loading__content]').should('not.exist');
    cy.get('[data-cy=account-management-forms]').scrollIntoView();
    cy.get('[data-cy=account-management-forms]').should('be.visible');

    cy.get('[data-cy=create-account__introduction__continue]').click();
    cy.get('[data-cy=create-account__premium__button__continue]').click();
    cy.get('[data-cy=create-account__fields__username]').type(username);
    cy.get('[data-cy=create-account__fields__password]').type(password);
    cy.get('[data-cy=create-account__fields__password-repeat]').type(password);
    cy.get('[data-cy=create-account__boxes__user-prompted] > label').click();
    cy.get('[data-cy=create-account__credentials__button__continue]').click();
    cy.get('[data-cy=create-account__submit-analytics__button__continue]').click();
    cy.get('[data-cy=account-management-forms]').should('not.exist');
    cy.updateAssets();
    this.loadEnv();
  }

  clear() {
    this.logout();
  }

  fasterLogin(username: string, password = '1234', disableModules = false) {
    cy.logout();
    cy.createAccount(username, password);
    if (disableModules)
      cy.disableModules();

    this.loadEnv();
    this.visit();
    this.login(username, password);
  }

  checkGetPremiumButton() {
    cy.get('[data-cy=get-premium-button]').should('be.visible');
  }

  relogin(username: string, password = '1234'): void {
    this.clear();
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
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('[data-cy=logout-button]').click();
    cy.get('[data-cy=confirm-dialog]').find('[data-cy=button-confirm]').click();
    cy.get('[data-cy=username-input] input').should('be.visible');
  }

  changeCurrency(currency: string) {
    cy.get('[data-cy=currency-dropdown]').click();
    cy.get(`#change-to-${currency.toLowerCase()}`).click();
  }

  togglePrivacyMenu(show?: boolean) {
    cy.get('[data-cy=privacy-menu]').as('menu');

    if (show) {
      cy.get('@menu').click();
      cy.get('[data-cy=privacy-menu-content]').should('exist');
      cy.get('[data-cy=privacy-menu-content]').should('be.visible');
    }
    else {
      cy.get('@menu').then(($menu) => {
        if ($menu.find('[data-cy=privacy-menu-content]').is(':visible')) {
          cy.get('@menu').click();
          cy.get('[data-cy=privacy-menu-content]').should('not.exist');
        }
      });
    }
  }

  changePrivacyMode(mode: number) {
    this.togglePrivacyMenu(true);
    cy.get(`[data-cy=privacy-mode-dropdown__input] + div > div:nth-child(${mode + 1})`).as('label');

    cy.get('@label').click();
    this.togglePrivacyMenu();
  }

  toggleScrambler(enable: boolean) {
    cy.get('[data-cy=privacy-mode-scramble__toggle] input[type=checkbox]').as('input');

    if (enable) {
      cy.get('@input').should('not.be.checked');
      cy.get('@input').check();
      cy.get('@input').should('be.checked');
    }
    else {
      cy.get('@input').should('be.checked');
      cy.get('@input').uncheck();
      cy.get('@input').should('not.be.checked');
    }
  }

  changeScrambleValue(multiplier: string) {
    this.toggleScrambler(true);
    cy.get('[data-cy=privacy-mode-scramble__multiplier]').as('input');

    cy.get('@input').type(multiplier);
  }

  changeRandomScrambleValue() {
    this.toggleScrambler(true);
    cy.get('[data-cy=privacy-mode-scramble__multiplier]').as('input');
    cy.get('[data-cy=privacy-mode-scramble__random-multiplier]').as('button');

    cy.get('@button').click();
  }

  /**
   * to get single query param values from route
   * @param {string} key
   * @param {string} value
   */
  shouldHaveQueryParam(key: string, value: string) {
    cy.location().should((loc) => {
      const query = new URLSearchParams(loc.href);
      expect(query.get(key), `query key ${key}`).to.equal(value);
    });
  }

  /**
   * Asserts that the current URL does not have the specified query parameter.
   *
   * @param {string} key - The query parameter key to check.
   * @return {void}
   */
  shouldNotHaveQueryParam(key: string): void {
    cy.location().should((loc) => {
      const query = new URLSearchParams(loc.href);
      // eslint-disable-next-line @typescript-eslint/no-unused-expressions
      expect(query.get(key), `query key ${key}`).to.be.null;
    });
  }

  static navigateTo(menu: string, submenu?: string) {
    const click = (selector: string, scroll = false) => {
      if (scroll) {
        cy.get(selector).scrollIntoView();
        cy.get(selector).should('be.visible');
      }
      cy.get(selector).trigger('mouseover');
      cy.get(selector).click();
    };

    const menuSelector = `[data-cy="navigation__${menu}"]`;
    cy.get(menuSelector).then((menuEl) => {
      const submenuWrapper = menuEl.find('[data-cy=submenu-wrapper]');
      if (submenuWrapper.length === 0 || submenuWrapper.attr('data-expanded') !== 'true')
        click(menuSelector, true);

      if (submenu) {
        cy.get(menuSelector).find('[data-cy=submenu-wrapper]').scrollIntoView();
        cy.get(menuSelector).find('[data-cy=submenu-wrapper]').should('be.visible');

        const subMenuSelector = `[data-cy="navigation__${submenu}"]`;
        click(subMenuSelector);
      }
    });
  }
}
