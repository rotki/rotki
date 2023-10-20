import { type ActionResult } from '@rotki/common/lib/data';
import { getValidSelectorFromEvmAddress } from '@/utils/assets';

export const setCheckBox = (selector: string, enabled = false) => {
  const slot = `${selector} label`;
  const input = `${selector} input`;

  cy.get(slot).should('be.visible');
  cy.get(input).should(enabled ? 'not.be.checked' : 'be.checked');
  cy.get(slot).click();
  cy.get(input).should(!enabled ? 'not.be.checked' : 'be.checked');
};

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

let counter = 0;

type QueryTarget = { method: 'POST' | 'GET'; url: string };

/**
 * Used to wait for an async query to complete.
 * The method will intercept the original query, get the task id
 *
 * @param url {@see cypress/types/net-stubbing#RouteMatcher} The url that returns the pending task id
 * @param timeout How long the util will wait for the /api/1/tasks/task_id to
 * complete
 */
export const waitForAsyncQuery = (
  { url, method }: QueryTarget,
  timeout = 120000
) => {
  const urlBase = url.indexOf('/api/1/') + '/api/1/'.length;
  const baseIdentifier = url.substr(urlBase).replace('/', '_');
  counter++;
  const queryIdentifier = `q_${counter}_${baseIdentifier}`;
  const taskIdentifier = `t_${counter}_${baseIdentifier}`;

  cy.intercept({
    url,
    method
  }).as(queryIdentifier);

  cy.wait(`@${queryIdentifier}`, { timeout })
    .its('response.body')
    .then(body => {
      cy.intercept({
        method: 'GET',
        url: `/api/1/tasks/${body.result.task_id}`
      }).as(taskIdentifier);
      cy.wait(`@${taskIdentifier}`, { timeout })
        .its('response.statusCode')
        .should('equal', 200);
    });
};

let mockId = 100_000;
const createResult = <T>(t: T): ActionResult<T> => ({
  message: '',
  result: t
});

const mockAsyncTaskBody = (): ActionResult<{ task_id: number }> =>
  createResult({
    task_id: mockId++
  });

export const mockRequest = (target: QueryTarget, data: any = {}) => {
  cy.intercept(target, {
    statusCode: 200,
    body: mockAsyncTaskBody()
  }).as('mockRequest');

  return () => {
    cy.wait('@mockRequest', { timeout: 30000 })
      .its('response.body')
      .then(body => {
        const taskId = body.result.task_id;
        let taskDone = false;
        cy.intercept(
          {
            method: 'GET',
            url: `/api/1/tasks/${taskId}`
          },
          {
            statusCode: 200,
            body: createResult({
              outcome: createResult(data),
              status: 'completed'
            })
          }
        ).as(`task-${taskId}`);

        cy.intercept(
          {
            method: 'GET',
            url: '/api/1/tasks'
          },
          req => {
            if (taskDone) {
              req.continue();
            } else {
              req.continue(res => {
                taskDone = true;
                res.body.result.completed = [taskId];
              });
            }
          }
        ).as('taskMonitor');
        cy.wait(`@task-${taskId}`, { timeout: 30000 });
      });
  };
};
