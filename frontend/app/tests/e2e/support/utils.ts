export function selectAsset(element: string, value: string) {
  cy.get(element).type(value);
  cy.get(`#asset-${value.toLocaleLowerCase()}`).click();
}
