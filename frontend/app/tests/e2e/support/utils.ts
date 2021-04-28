export function selectAsset(element: string, value: string, id?: string) {
  cy.get(element).type(value);
  const identifier = (id ?? value).toLocaleLowerCase();
  cy.get(`#asset-${identifier}`).click();
}
