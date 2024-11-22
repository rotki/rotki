import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  visit() {
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('[data-cy=settings-button]').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('a.settings__general').click();
  }

  setInputFieldValue(selector: string, value: string) {
    cy.get(`${selector} input`).as('input');
    cy.get('@input').clear();
    cy.get('@input').type(value);
    cy.get('@input').blur();
  }

  setFloatingPrecision(value: string) {
    this.setInputFieldValue('[data-cy=floating-precision-settings]', value);
  }

  changeAnonymousUsageStatistics() {
    cy.get('[data-cy=anonymous-usage-statistics-input]').click();
    this.confirmInlineSuccess('[data-cy=anonymous-usage-statistics-input] .details .text-rui-success');
  }

  selectCurrency(value: string) {
    cy.get('[data-cy=currency-selector]').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  selectChainToIgnore(value: string) {
    cy.get('[data-cy=chains-to-skip-detection] [class*=icon__wrapper]').click();
    cy.get('[data-cy=chains-to-skip-detection] input').should('not.be.disabled');
    cy.get('[data-cy=chains-to-skip-detection] input').type(value);
    cy.get('[role=menu-content] button').should('have.length', 1);
    cy.get('[data-cy=chains-to-skip-detection] input').type('{enter}');
    cy.get('[data-cy=chains-to-skip-detection] [class*=icon__wrapper]').click();
    this.confirmInlineSuccess(
      '[data-cy=chains-to-skip-detection] .details',
      'EVM Chains for which to skip automatic token detection saved successfully',
    );
    cy.get('[data-cy=chains-to-skip-detection] .details').should('be.empty');
  }

  setBalanceSaveFrequency(value: string) {
    this.setInputFieldValue('[data-cy=balance-save-frequency-input]', value);
  }

  setDateDisplayFormat(value: string) {
    this.setInputFieldValue('[data-cy=date-display-format-input]', value);
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.confirmFieldMessage({ target, messageContains, mustInclude: 'Setting saved' });
  }

  verify(settings: {
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    thousandSeparator: string;
    decimalSeparator: string;
    evmchainsToSkipDetection: string[];
    currencyLocation: 'after' | 'before';
    currency: string;
    balanceSaveFrequency: string;
  }) {
    cy.get('[data-cy=floating-precision-settings] input').should('have.value', settings.floatingPrecision);
    cy.get('[data-cy=anonymous-usage-statistics-input]').should(
      settings.anonymousUsageStatistics ? 'be.checked' : 'not.be.checked',
    );
    cy.get('[data-cy=currency-selector] input').should('have.value', settings.currency);
    cy.get('[data-cy=balance-save-frequency-input] input').should('have.value', settings.balanceSaveFrequency);

    this.verifySkipped(settings.evmchainsToSkipDetection);

    cy.get('[data-cy=date-display-format-input] input').should('have.value', settings.dateDisplayFormat);
    cy.get('[data-cy=thousand-separator-input] input').should('have.value', settings.thousandSeparator);
    cy.get('[data-cy=decimal-separator-input] input').should('have.value', settings.decimalSeparator);

    cy.get('[data-cy=currency-location-input] input').should('have.length', 2);
    cy.get('[data-cy=currency-location-input] input:checked').should('have.value', settings.currencyLocation);
  }

  verifySkipped(entries: string[]): void {
    entries.forEach((item) => {
      cy.get(`[data-cy=chains-to-skip-detection] [data-value=${item}]`).should('exist');
    });
  }

  navigateAway() {
    RotkiApp.navigateTo('dashboard');
  }
}
