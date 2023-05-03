export class AssetsManagerPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__asset-manager').scrollIntoView();
    cy.get('.navigation__asset-manager').click();
    cy.get('[data-cy="managed-assets-table"]').should('be.visible');
  }

  ignoredAssets() {
    cy.get('[data-cy=asset-filter]').click();
    return cy
      .get('[data-cy=asset-filter-ignored] .v-radio:nth-child(3)')
      .invoke('text')
      .then(text => {
        cy.get('[data-cy=asset-filter]').click();
        cy.wrap(text.replace(/[^\d.]/g, ''));
      });
  }

  ignoredAssetCount(number: number) {
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('be.visible');
    cy.get('[data-cy=asset-filter-ignored] .v-radio:nth-child(3)').should(
      'include.text',
      number.toString()
    );
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('not.be.visible');
  }

  searchAsset(asset: string) {
    cy.get('[data-cy=asset_table_filter]').type(
      `{selectall}{backspace}symbol: ${asset}{enter}{esc}`
    );
    cy.get('.v-data-table__empty-wrapper').should('not.exist');
    cy.get('.v-data-table__progress').should('not.exist');
  }

  addIgnoredAsset(asset: string) {
    this.searchAsset(asset);

    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'false');
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).click();
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).then(() => {
        expect($switch.attr('aria-checked')).not.to.eq(initialValue);
      });
    });
  }

  selectShowAll(): void {
    cy.get('[data-cy=asset-filter]').scrollIntoView();
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('be.visible');
    cy.get(
      '[data-cy=asset-filter-ignored] .v-radio:first-child'
    ).scrollIntoView();
    cy.get('[data-cy=asset-filter-ignored] .v-radio:first-child').click();
    cy.get('[data-cy=asset-filter]').click();
    cy.get('[data-cy=asset-filter-menu]').should('not.be.visible');
  }

  removeIgnoredAsset(asset: string) {
    this.searchAsset(asset);
    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'true');
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).click();
      cy.get(
        '.v-data-table__wrapper tbody tr:first-child td:nth-child(6)'
      ).then(() => {
        expect($switch.attr('aria-checked')).not.to.eq(initialValue);
      });
    });
  }
}
