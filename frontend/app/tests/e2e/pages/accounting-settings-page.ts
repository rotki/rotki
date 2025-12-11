export class AccountingSettingsPage {
  visit() {
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('[data-cy=settings-button]').click();
    cy.get('[data-cy="settings__accounting"]').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
  }

  setTaxFreePeriodDays(value: string) {
    cy.get('[data-cy=taxfree-period]').clear();
    cy.get('[data-cy=taxfree-period]').type(value);
    cy.get('[data-cy=taxfree-period] input').blur();
    this.confirmInlineSuccess('[data-cy=taxfree-period]', value);
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
