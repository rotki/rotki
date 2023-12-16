export class AccountingSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings__accounting').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
  }

  setTaxFreePeriodDays(value: string) {
    cy.get('.accounting-settings__taxfree-period-days input').clear();
    cy.get('.accounting-settings__taxfree-period-days input').type(value);
    cy.get('.accounting-settings__taxfree-period-days input').blur();
    this.confirmInlineSuccess('.accounting-settings__taxfree-period-days .details', value);
  }

  changeSwitch(target: string, enabled: boolean) {
    cy.get(`${target}`).scrollIntoView();
    cy.get(`${target}`).should('be.visible');
    this.verifySwitchState(target, !enabled);
    cy.get(`${target} input`).click();
    this.verifySwitchState(target, enabled);
    this.confirmInlineSuccess(`${target} .details .text-rui-success`);
  }

  verifySwitchState(target: string, enabled: boolean) {
    cy.get(`${target} input`).should(enabled ? 'be.checked' : 'not.be.checked');
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.confirmFieldMessage({ target, messageContains, mustInclude: 'Setting saved' });
  }
}
