import { RotkiApp } from './rotki-app';

export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('.user-dropdown__settings').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('a.settings__general').click();
  }

  setInputFieldValue(selector: string, value: string) {
    cy.get(selector).as('input');
    cy.get('@input').clear();
    cy.get('@input').type(value);
    cy.get('@input').blur();
  }

  setFloatingPrecision(value: string) {
    this.setInputFieldValue('.general-settings__fields__floating-precision input', value);
  }

  changeAnonymousUsageStatistics() {
    cy.get('.general-settings__fields__anonymous-usage-statistics input').click();
    this.confirmInlineSuccess('.general-settings__fields__anonymous-usage-statistics .details .text-rui-success');
  }

  selectCurrency(value: string) {
    cy.get('.general-settings__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  selectChainToIgnore(value: string) {
    cy.get('.general-settings__fields__account-chains-to-skip-detection [class*=icon__wrapper]').click();
    cy.get('[data-cy=account-chain-skip-detection-field] input').should('not.be.disabled');
    cy.get('[data-cy=account-chain-skip-detection-field] input').type(value);
    cy.get('[role=menu-content] button').should('have.length', 1);
    cy.get('[data-cy=account-chain-skip-detection-field] input').type('{enter}');
  }

  setBalanceSaveFrequency(value: string) {
    this.setInputFieldValue('.general-settings__fields__balance-save-frequency input', value);
  }

  setDateDisplayFormat(value: string) {
    this.setInputFieldValue('.general-settings__fields__date-display-format input', value);
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
    cy.get('.general-settings__fields__floating-precision input').should('have.value', settings.floatingPrecision);
    cy.get('.general-settings__fields__anonymous-usage-statistics input').should(
      settings.anonymousUsageStatistics ? 'be.checked' : 'not.be.checked',
    );
    cy.get('.general-settings__fields__currency-selector [data-id="activator"] span[class*=_value_]').should(
      'contain.text',
      settings.currency,
    );
    cy.get('.general-settings__fields__balance-save-frequency input').should(
      'have.value',
      settings.balanceSaveFrequency,
    );

    settings.evmchainsToSkipDetection.forEach((item) => {
      cy.get(`.general-settings__fields__account-chains-to-skip-detection [role=button][data-value=${item}]`).should(
        'exist',
      );
    });
    cy.get('.general-settings__fields__date-display-format input').should('have.value', settings.dateDisplayFormat);
    cy.get('.general-settings__fields__thousand-separator input').should('have.value', settings.thousandSeparator);
    cy.get('.general-settings__fields__decimal-separator input').should('have.value', settings.decimalSeparator);
    cy.get('.general-settings__fields__currency-location input').should('have.length', 2);
    cy.get(`.general-settings__fields__currency-location input:checked`).should(
      'have.value',
      settings.currencyLocation,
    );
  }

  navigateAway() {
    RotkiApp.navigateTo('dashboard');
  }
}
