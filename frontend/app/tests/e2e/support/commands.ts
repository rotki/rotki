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
import { type ExternalTrade } from './types';

const backendUrl = Cypress.env('BACKEND_URL');

const logout = () => {
  cy.request({
    url: `${backendUrl}/api/1/users`,
    method: 'GET',
    failOnStatusCode: false
  })
    .its('body')
    .then(body => {
      const result = body.result;
      if (!result) {
        return;
      }

      const loggedUsers = Object.keys(result).filter(
        user => result[user] === 'loggedin'
      );

      if (loggedUsers.length !== 1) {
        return;
      }

      const user = loggedUsers[0];

      return cy
        .request({
          url: `${backendUrl}/api/1/users/${user}`,
          method: 'PATCH',
          failOnStatusCode: false,
          body: {
            action: 'logout'
          }
        })
        .its('body')
        .then(body => body.result);
    });
};

const updateAssets = () => {
  cy.request({
    url: `${backendUrl}/api/1/assets/updates`,
    method: 'DELETE',
    body: {
      reset: 'soft'
    },
    failOnStatusCode: false
  })
    .its('body')
    .then(body => {
      const result = body.result;
      if (result) {
        cy.log(`asset reset completed: ${JSON.stringify(result)}`);
      }
    });
};

const disableModules = () => {
  cy.request({
    url: `${backendUrl}/api/1/settings`,
    method: 'PUT',
    body: {
      settings: {
        active_modules: []
      }
    },
    failOnStatusCode: false
  })
    .its('body')
    .then(body => {
      const result = body.result;
      if (result) {
        cy.log(`settings updated: ${JSON.stringify(result.active_modules)}`);
      }
    });
};

const createAccount = (username: string, password = '1234') =>
  cy
    .request({
      url: `${backendUrl}/api/1/users`,
      method: 'PUT',
      body: {
        name: username,
        password,
        initial_settings: {
          submit_usage_analytics: true
        }
      },
      failOnStatusCode: false
    })
    .its('body');

const addExternalTrade = (trade: ExternalTrade) =>
  cy
    .request({
      url: `${backendUrl}/api/1/trades`,
      method: 'PUT',
      body: {
        timestamp: new Date(trade.time).getTime() / 1000,
        location: trade.location || 'external',
        base_asset: trade.base_id,
        quote_asset: trade.quote_id,
        trade_type: trade.trade_type,
        amount: trade.amount,
        rate: trade.rate,
        fee: trade.fee,
        fee_currency: trade.fee_id,
        link: trade.link,
        notes: trade.notes
      }
    })
    .its('body');

const addEtherscanKey = (key: string) =>
  cy
    .request({
      url: `${backendUrl}/api/1/external_services`,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: {
        services: [{ name: 'etherscan', api_key: key }]
      },
      failOnStatusCode: false
    })
    .its('status');

/**
 * Wait for the element to not exist.
 * Once it doesn't exist, for the next 1 seconds, check if the element ever appears again.
 * If it doesn't appear again, we can continue.
 * But if it appears again, run the check again from the start.
 */
const assertNoRunningTasks = () => {
  const selector = '[data-cy=notification-indicator-progress]';
  cy.get(selector)
    .should('not.exist')
    .then(() => {
      // eslint-disable-next-line cypress/no-unnecessary-waiting
      cy.wait(1000);

      cy.get('body').then($body => {
        if ($body.find(selector).length > 0) {
          cy.assertNoRunningTasks();
        }
      });
    });
};

Cypress.Commands.add('logout', logout);
Cypress.Commands.add('updateAssets', updateAssets);
Cypress.Commands.add('disableModules', disableModules);
Cypress.Commands.add('createAccount', createAccount);
Cypress.Commands.add('addExternalTrade', addExternalTrade);
Cypress.Commands.add('addEtherscanKey', addEtherscanKey);
Cypress.Commands.add('assertNoRunningTasks', assertNoRunningTasks);
