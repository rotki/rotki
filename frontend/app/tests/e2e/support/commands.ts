// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add("login", (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This is will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... });
import type { FieldMessage } from './types';

const backendUrl = Cypress.env('BACKEND_URL');

const WAIT_TIME_MS = 5000;
const TIMEOUT_MS = 120000;
const MAX_RETRIES = TIMEOUT_MS / WAIT_TIME_MS;

let currentRetry = 1;

function logout() {
  cy.request({
    url: `${backendUrl}/api/1/users`,
    method: 'GET',
    failOnStatusCode: false,
  })
    .its('body')
    .then((body) => {
      const result = body.result;
      if (!result)
        return;

      const loggedUsers = Object.keys(result).filter(user => result[user] === 'loggedin');

      if (loggedUsers.length !== 1)
        return;

      const user = loggedUsers[0];

      return cy
        .request({
          url: `${backendUrl}/api/1/users/${user}`,
          method: 'PATCH',
          failOnStatusCode: false,
          body: {
            action: 'logout',
          },
        })
        .its('body')
        .then(body => body.result);
    });
}

function updateAssets() {
  cy.request({
    url: `${backendUrl}/api/1/assets/updates`,
    method: 'DELETE',
    body: {
      reset: 'soft',
    },
    failOnStatusCode: false,
  }).its('body').then((body) => {
    const result = body.result;
    if (result)
      cy.log(`asset reset completed: ${JSON.stringify(result)}`);
  });
}

function disableModules() {
  cy.request({
    url: `${backendUrl}/api/1/settings`,
    method: 'PUT',
    body: {
      settings: {
        active_modules: [],
      },
    },
    failOnStatusCode: false,
  }).its('body').then((body) => {
    const result = body.result;
    if (result)
      cy.log(`settings updated: ${JSON.stringify(result.active_modules)}`);
  });
}

/**
 * Checks for the completion of a task by querying the backend API.
 * If the task is not yet completed, it retries the request after a delay.
 *
 * @param {Object} result - The result object containing the task ID.
 * @param {Object} [result.result] - The result property of the result object.
 * @param {number} [result.result.task_id] - The ID of the task to check for completion.
 * @return {void} - This function doesn’t return a value.
 */
function checkForTaskCompletion(result: { result?: { task_id?: number } }): void {
  cy.request({
    url: `${backendUrl}/api/1/tasks`,
    method: 'GET',
  }).then((resp) => {
    const taskId = result.result?.task_id;
    if (
      resp.status === 200
      && resp.body.result
      && resp.body.result.completed
      && Array.isArray(resp.body.result.completed)
      && resp.body.result.completed.includes(taskId)
    ) {
      cy.request({
        url: `${backendUrl}/api/1/tasks/${taskId}`,
        method: 'GET',
      });
      return;
    }

    // introduce some delay between tries since we don't want to stress the backend
    // eslint-disable-next-line cypress/no-unnecessary-waiting
    cy.wait(WAIT_TIME_MS);

    currentRetry++;
    if (currentRetry > MAX_RETRIES)
      throw new Error('Exceeded maximum retries for task completion check');

    checkForTaskCompletion(result);
  });
}

function createAccount(username: string, password = '1234') {
  currentRetry = 1;
  return cy.request({
    url: `${backendUrl}/api/1/users`,
    method: 'PUT',
    timeout: 120000,
    body: {
      name: username,
      password,
      initial_settings: {
        submit_usage_analytics: true,
      },
      async_query: true,
    },
    failOnStatusCode: false,
  }).its('body').then(checkForTaskCompletion);
}

function addEtherscanKey(key: string) {
  return cy.request({
    url: `${backendUrl}/api/1/external_services`,
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: {
      services: [{ name: 'etherscan', api_key: key }],
    },
    failOnStatusCode: false,
  }).its('status');
}

/**
 * Wait for the element to not exist.
 * Once it doesn't exist, for the next 1 seconds, check if the element ever appears again.
 * If it doesn't appear again, we can continue.
 * But if it appears again, run the check again from the start.
 */
function assertNoRunningTasks() {
  const selector = '[data-cy=notification-indicator-progress]';
  cy.get(selector)
    .should('not.exist')
    .then(() => {
      // eslint-disable-next-line cypress/no-unnecessary-waiting
      cy.wait(1000);

      cy.get('body').then(($body) => {
        if ($body.find(selector).length > 0)
          cy.assertNoRunningTasks();
      });
    });
}

function confirmFieldMessage({ target, mustInclude, messageContains }: FieldMessage) {
  cy.get(target).as('message');
  cy.get('@message').scrollIntoView();
  cy.get('@message').should('be.visible');
  cy.get('@message').should('include.text', mustInclude);
  if (messageContains)
    cy.get('@message').should('include.text', messageContains);
}

function scrollElemToTop(target: string) {
  cy.get(target).then(($el) => {
    // Get the element's offset from the top of the page
    const offset = $el.offset();

    // Scroll to the position of the element
    if (offset !== undefined) {
      cy.get('body').then(($body) => {
        $body[0].scrollTo(0, offset.top);
      });
    }

    cy.wrap($el).should('be.visible', { timeout: 1000 });
  });
}

Cypress.Commands.add('logout', logout);
Cypress.Commands.add('updateAssets', updateAssets);
Cypress.Commands.add('disableModules', disableModules);
Cypress.Commands.add('createAccount', createAccount);
Cypress.Commands.add('addEtherscanKey', addEtherscanKey);
Cypress.Commands.add('assertNoRunningTasks', assertNoRunningTasks);
Cypress.Commands.add('confirmFieldMessage', confirmFieldMessage);
Cypress.Commands.add('scrollElemToTop', scrollElemToTop);
