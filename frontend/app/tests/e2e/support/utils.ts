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

/**
 * Used to wait for an async query to complete.
 * The method will intercept the original query, get the task id
 *
 * @param url {@see cypress/types/net-stubbing#RouteMatcher} The url that returns the pending task id
 * @param timeout How long the util will wait for the /api/1/tasks/task_id to
 * complete
 */
export const waitForAsyncQuery = (
  url: { method: 'POST' | 'GET'; url: string },
  timeout = 120000
) => {
  cy.intercept(url).as('asyncQuery');

  cy.wait('@asyncQuery', { timeout })
    .its('response.body')
    .then(body => {
      cy.intercept({
        method: 'GET',
        url: `/api/1/tasks/${body.result.task_id}`
      }).as('task');
      cy.wait('@task', { timeout })
        .its('response.statusCode')
        .should('equal', 200);
    });
};
