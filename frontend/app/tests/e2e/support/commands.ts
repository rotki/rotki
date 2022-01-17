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
    url: 'http://localhost:22221/api/1//settings',
    method: 'PUT',
    body: {
      active_modules: []
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

Cypress.Commands.add('logout', logout);
Cypress.Commands.add('updateAssets', updateAssets);
Cypress.Commands.add('disableModules', disableModules);
