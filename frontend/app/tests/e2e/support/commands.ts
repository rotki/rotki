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
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })

import { ExternalLedgerAction, ExternalTrade } from './types';

const logout = () => {
  cy.request({
    url: 'http://localhost:22221/api/1/users',
    method: 'GET'
  })
    .its('body')
    .then(body => {
      const result = body.result;
      if (result) {
        const loggedUsers = Object.keys(result).filter(
          user => result[user] === 'loggedin'
        );
        if (loggedUsers.length === 1) {
          const user = loggedUsers[0];
          cy.request({
            url: `http://localhost:22221/api/1/users/${user}`,
            method: 'PATCH',
            body: {
              action: 'logout'
            }
          });
        }
      }
    });
};

const updateAssets = () => {
  cy.request({
    url: 'http://localhost:22221/api/1/assets/updates',
    method: 'DELETE',
    body: {
      reset: 'soft'
    }
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
    url: 'http://localhost:22221/api/1/settings',
    method: 'PUT',
    body: {
      settings: {
        active_modules: []
      }
    }
  })
    .its('body')
    .then(body => {
      const result = body.result;
      if (result) {
        cy.log(`settings updated: ${JSON.stringify(result['active_modules'])}`);
      }
    });
};

const createAccount = (username: string, password: string = '1234') => {
  cy.logout();
  return cy
    .request({
      url: 'http://localhost:22221/api/1/users',
      method: 'PUT',
      body: {
        name: username,
        password: password,
        initial_settings: {
          submit_usage_analytics: true
        }
      }
    })
    .its('body');
};

const addExternalTrade = (trade: ExternalTrade) => {
  return cy
    .request({
      url: 'http://localhost:22221/api/1/trades',
      method: 'PUT',
      body: {
        timestamp: new Date(trade.time).getTime() / 1000,
        location: 'external',
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
};

const addLedgerAction = (action: ExternalLedgerAction) => {
  return cy
    .request({
      url: 'http://localhost:22221/api/1/ledgeractions',
      method: 'PUT',
      body: {
        timestamp: new Date(action.datetime).getTime() / 1000,
        action_type: action.action_type,
        location: action.location,
        amount: action.amount,
        asset: action.asset_id,
        rate: action.rate,
        rate_asset: action.rate_asset_id,
        link: action.link,
        notes: action.notes
      }
    })
    .its('body');
};

const addEtherscanKey = (key: string) => {
  return cy
    .request({
      url: 'http://localhost:22221/api/1/external_services',
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json; charset=utf-8'
      },
      body: {
        services: [{ name: 'etherscan', api_key: key }]
      }
    })
    .its('status');
};

Cypress.Commands.add('logout', logout);
Cypress.Commands.add('updateAssets', updateAssets);
Cypress.Commands.add('disableModules', disableModules);
Cypress.Commands.add('createAccount', createAccount);
Cypress.Commands.add('addExternalTrade', addExternalTrade);
Cypress.Commands.add('addLedgerAction', addLedgerAction);
Cypress.Commands.add('addEtherscanKey', addEtherscanKey);
