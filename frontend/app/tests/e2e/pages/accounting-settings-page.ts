export class AccountingSettingsPage {
  visit() {
    cy.get('.user-dropdown').click();
    cy.get('[data-cy=user-dropdown]').should('be.visible');
    cy.get('.user-dropdown__settings').click();
    cy.get('a.settings__accounting').click();
    cy.get('[data-cy=user-dropdown]').should('not.be.visible');
  }

  setTaxFreePeriodDays(value: string) {
    cy.get('.accounting-settings__taxfree-period-days input').clear();
    cy.get('.accounting-settings__taxfree-period-days input').type(value);
    cy.get('.accounting-settings__taxfree-period-days input').blur();
    this.confirmInlineSuccess(
      '.accounting-settings__taxfree-period-days .details',
      value
    );
  }

  changeSwitch(target: string, enabled: boolean) {
    cy.get(`${target}`).scrollIntoView();
    cy.get(`${target}`).should('be.visible');
    cy.get(`${target} input`).should(
      'have.attr',
      'aria-checked',
      (!enabled).toString()
    );
    cy.get(target).click();
    cy.get(`${target} input`).should(
      'have.attr',
      'aria-checked',
      enabled.toString()
    );
    this.confirmInlineSuccess(`${target} .v-messages__message`);
  }

  verifySwitchState(target: string, enabled: boolean) {
    cy.get(`${target} input`).should(
      'have.attr',
      'aria-checked',
      enabled.toString()
    );
  }

  confirmInlineSuccess(target: string, messageContains?: string) {
    cy.get(target).as('message');
    cy.get('@message').should('be.visible');
    cy.get('@message').should('include.text', 'Setting saved');
    if (messageContains) {
      cy.get('@message').should('include.text', messageContains);
    }
  }
}
