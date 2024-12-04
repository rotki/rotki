import { hexToRgbPoints } from '@rotki/common';

export class TagManager {
  addTag(parent: string, name: string, description: string, background?: string, foreground?: string) {
    cy.get(`${parent} [data-cy=add-tag-button]`).click();
    cy.get('[data-cy=tag-creator-name]').type(name);
    cy.get('[data-cy=tag-creator-description]').type(description);
    if (background && foreground) {
      cy.get('[data-cy=tag-creator__color-picker__background] input').clear();
      cy.get('[data-cy=tag-creator__color-picker__background] input').type(background);
      cy.get('[data-cy=tag-creator__color-picker__background] [data-cy=color-display]').should(
        'css',
        'background-color',
        `rgb(${hexToRgbPoints(background).join(', ')})`,
      );

      cy.get('[data-cy=tag-creator__color-picker__foreground] input').clear();
      cy.get('[data-cy=tag-creator__color-picker__foreground] input').type(foreground);
      cy.get('[data-cy=tag-creator__color-picker__foreground] [data-cy=color-display]').should(
        'css',
        'background-color',
        `rgb(${hexToRgbPoints(foreground).join(', ')})`,
      );
    }
    cy.get('[data-cy=bottom-dialog] [data-cy=confirm]').last().click();
  }
}
