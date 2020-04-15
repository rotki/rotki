export class GeneralSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('.user-dropdown__settings').click();
  }

  setFloatingPrecision(value: string) {
    cy.get('.settings-general__fields__floating-precision input').clear();
    cy.get('.settings-general__fields__floating-precision').type(value);
  }

  changeAnonymizedLogs() {
    cy.get('.settings-general__fields__anonymized-logs').click();
  }

  changeAnonymousUsageStatistics() {
    cy.get('.settings-general__fields__anonymous-usage-statistics').click();
  }

  setHistoryDataStart(value: string) {
    cy.get('.settings-general__fields__historic-data-start input').clear();
    cy.get('.settings-general__fields__historic-data-start')
      .type(value)
      .click();
  }

  selectCurrency(value: string) {
    cy.get('.settings-general__fields__currency-selector').click();
    cy.get(`#currency__${value.toLocaleLowerCase()}`).click();
  }

  setBalanceSaveFrequency(value: string) {
    cy.get('.settings-general__fields__balance-save-frequency input').clear();
    cy.get('.settings-general__fields__balance-save-frequency').type(value);
  }

  setDateDisplayFormat(value: string) {
    cy.get('.settings-general__fields__date-display-format input').clear();
    cy.get('.settings-general__fields__date-display-format').type(value);
  }

  saveSettings() {
    cy.get('.settings-general__buttons__save').click();
  }

  confirmSuccess() {
    cy.get('.message-dialog__title').should('include.text', 'Success');
    cy.get('.message-dialog__buttons__confirm').click();
  }

  verify(settings: {
    anonymizedLogs: boolean;
    anonymousUsageStatistics: boolean;
    floatingPrecision: string;
    dateDisplayFormat: string;
    currency: string;
    balanceSaveFrequency: string;
    historicDataStart: string;
    rpcEndpoint: string;
  }) {
    cy.get('.settings-general__fields__floating-precision input').should(
      'have.value',
      settings.floatingPrecision
    );
    cy.get('.settings-general__fields__anonymized-logs input')
      .should('have.attr', 'aria-checked')
      .and('include', `${settings.anonymizedLogs}`);
    cy.get('.settings-general__fields__anonymous-usage-statistics input')
      .should('have.attr', 'aria-checked')
      .and('include', `${settings.anonymousUsageStatistics}`);
    cy.get('.settings-general__fields__historic-data-start input').should(
      'have.value',
      settings.historicDataStart
    );
    cy.get(
      '.settings-general__fields__currency-selector .v-select__selection'
    ).should('have.text', settings.currency);
    cy.get('.settings-general__fields__balance-save-frequency input').should(
      'have.value',
      settings.balanceSaveFrequency
    );
    cy.get('.settings-general__fields__date-display-format input').should(
      'have.value',
      settings.dateDisplayFormat
    );
    this.verifyRPCEndpoint(settings.rpcEndpoint);
  }

  verifyRPCEndpoint(rpcEndpoint: string) {
    cy.get('.settings-general__fields__rpc-endpoint input').should(
      'have.value',
      rpcEndpoint
    );
  }

  navigateAway() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__otc-trades').click();
  }

  setRpcEndpoint(value: string) {
    cy.get('.settings-general__fields__rpc-endpoint input').clear();
    cy.get('.settings-general__fields__rpc-endpoint').type(value);
  }

  confirmFailure() {
    cy.get('.message-dialog__title').should('include.text', 'Settings Error');
    cy.get('.message-dialog__buttons__confirm').click();
  }
}
