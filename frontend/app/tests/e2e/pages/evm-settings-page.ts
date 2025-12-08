import { RotkiApp } from './rotki-app';

export class EvmSettingsPage {
  visit(): void {
    cy.get('[data-cy=user-menu-button]').click();
    cy.get('[data-cy=user-dropdown]').should('exist');
    cy.get('[data-cy=settings-button]').click();
    cy.get('[data-cy=user-dropdown]').should('not.exist');
    cy.get('a.settings__evm').click();
  }

  confirmInlineSuccess(target: string, messageContains?: string): void {
    cy.confirmFieldMessage({ target, messageContains, mustInclude: 'Setting saved' });
  }

  navigateAway(): void {
    RotkiApp.navigateTo('dashboard');
  }

  // Indexer Order Settings
  getIndexerOrderSection(): Cypress.Chainable {
    return cy.get('[data-cy=indexer-order-setting]');
  }

  clickAddChainButton(): void {
    cy.get('[data-cy=add-chain-button]').click();
  }

  isAddChainButtonDisabled(): Cypress.Chainable<boolean> {
    return cy.get('[data-cy=add-chain-button]').then($btn => $btn.is(':disabled'));
  }

  selectChainFromMenu(chainId: string): void {
    cy.get('[data-cy=chain-menu]').should('be.visible');
    cy.get(`[data-cy=chain-menu-item-${chainId}]`).click();
  }

  addChain(chainId: string): void {
    this.clickAddChainButton();
    this.selectChainFromMenu(chainId);
  }

  removeChain(chainId: string): void {
    cy.get(`[data-cy=remove-chain-${chainId}]`).click();
  }

  selectTab(tabId: string): void {
    cy.get(`[data-cy=indexer-tab-${tabId}]`).click();
  }

  verifyTabExists(tabId: string): void {
    cy.get(`[data-cy=indexer-tab-${tabId}]`).should('exist');
  }

  verifyTabNotExists(tabId: string): void {
    cy.get(`[data-cy=indexer-tab-${tabId}]`).should('not.exist');
  }

  verifyDefaultIndexerOrder(indexers: string[]): void {
    cy.get('[data-cy=default-indexer-order] [data-cy^=prioritized-list-item-]').should('have.length', indexers.length);
    indexers.forEach((indexer, index) => {
      cy.get('[data-cy=default-indexer-order] [data-cy^=prioritized-list-item-]')
        .eq(index)
        .should('contain.text', indexer);
    });
  }

  verifyChainIndexerOrder(chainId: string, indexers: string[]): void {
    cy.get(`[data-cy=chain-indexer-order-${chainId}] [data-cy^=prioritized-list-item-]`).should('have.length', indexers.length);
    indexers.forEach((indexer, index) => {
      cy.get(`[data-cy=chain-indexer-order-${chainId}] [data-cy^=prioritized-list-item-]`)
        .eq(index)
        .should('contain.text', indexer);
    });
  }

  // Chains to Skip Detection Settings
  selectChainToIgnore(value: string): void {
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

  verifySkipped(entries: string[]): void {
    entries.forEach((item) => {
      cy.get(`[data-cy=chains-to-skip-detection] [data-value=${item}]`).should('exist');
    });
  }
}
