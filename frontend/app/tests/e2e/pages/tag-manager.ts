export class TagManager {
  addTag(
    parent: string,
    name: string,
    description: string,
    background?: string,
    foreground?: string
  ) {
    cy.get(`${parent} .tag-input__manage-tags`).click();
    cy.get('.tag_creator__name').type(name);
    cy.get('.tag_creator__description').type(description);
    if (background && foreground) {
      cy.get(
        '.tag-creator__color-picker__background .v-color-picker__input input'
      ).clear();
      cy.get(
        '.tag-creator__color-picker__background .v-color-picker__input input'
      ).type(background);
      cy.get(
        '.tag-creator__color-picker__foreground .v-color-picker__input input'
      ).clear();
      cy.get(
        '.tag-creator__color-picker__foreground .v-color-picker__input input'
      ).type(foreground);
    }
    cy.get('.tag-creator__buttons__save').click();
    cy.get('.tag-manager__close').click();
  }
}
