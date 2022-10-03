export class AssetsManagerPage {
  visit() {
    cy.get('.v-app-bar__nav-icon').click();
    cy.get('.navigation__asset-manager').click();
  }

  ignoredAssets() {
    return cy
      .get('.asset_management__ignored-assets__chip')
      .invoke('text')
      .then(text => {
        cy.wrap(text);
      });
  }

  ignoredAssetCount(number: number) {
    cy.get('.asset_management__ignored-assets__chip').should(
      'include.text',
      number.toString()
    );
  }

  searchAsset(asset: string) {
    cy.get('[data-cy=asset_table_filter]').type(
      `{selectall}{backspace}symbol: ${asset}{enter}{esc}`
    );
  }

  addIgnoredAsset(asset: string) {
    this.searchAsset(asset);
    cy.wait(1000);
    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'false');
      cy.get('.v-data-table__wrapper tbody tr:first-child td:nth-child(6)')
        .click()
        .then(() => {
          expect($switch.attr('aria-checked')).not.to.eq(initialValue);
        });
    });
  }

  removeIgnoredAsset(asset: string) {
    this.searchAsset(asset);
    cy.wait(1000);
    cy.get(
      '.v-data-table__wrapper tbody tr:first-child td:nth-child(6) input'
    ).then($switch => {
      const initialValue = $switch.attr('aria-checked');
      expect(initialValue, 'true');
      cy.get('.v-data-table__wrapper tbody tr:first-child td:nth-child(6)')
        .click()
        .then(() => {
          expect($switch.attr('aria-checked')).not.to.eq(initialValue);
        });
    });
  }
}
