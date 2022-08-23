import { getValidSelectorFromEvmAddress } from '@/utils/assets';

export function selectAsset(element: string, value: string, id?: string) {
  cy.get(element).type(value);
  const identifier = getValidSelectorFromEvmAddress(
    (id ?? value).toLocaleLowerCase()
  );
  cy.get(`#asset-${identifier}`).click();
}

export function selectLocation(element: string, value: string) {
  cy.get(element).type(value);
  const identifier = value.toLocaleLowerCase();
  cy.get(`#balance-location__${identifier}`).click();
}
