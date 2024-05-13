export class TagManager {
  addTag(
    parent: string,
    name: string,
    description: string,
    background?: string,
    foreground?: string,
  ) {
    cy.get(`${parent} .tag-input__manage-tags`).click();
    cy.get('.tag_creator__name').type(name);
    cy.get('.tag_creator__description').type(description);
    if (background && foreground) {
      cy.get(
        '[data-cy=tag-creator__color-picker__background] input',
      ).clear();
      cy.get(
        '[data-cy=tag-creator__color-picker__background] input',
      ).type(background);
      cy.get(
        '[data-cy=tag-creator__color-picker__foreground] input',
      ).clear();
      cy.get(
        '[data-cy=tag-creator__color-picker__foreground] input',
      ).type(foreground);
    }
    cy.get('[data-cy=tag-creator__buttons__save]').click();
  }
}
