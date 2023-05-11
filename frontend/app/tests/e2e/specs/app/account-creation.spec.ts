import { Guid } from '../../common/guid';
import { RotkiApp } from '../../pages/rotki-app';

describe('accounts', () => {
  let username: string;
  let app: RotkiApp;

  const viewPortSizes = [
    [1280, 720, 'HD Ready'],
    [1000, 660, 'Cypress default viewport'],
    [800, 600, 'Rotki minimum supported resolution'],
    [640, 480, 'Small res to simulate high app scaling or zoom']
  ];

  before(() => {
    app = new RotkiApp();
    app.visit();
  });

  viewPortSizes.forEach(size => {
    context(`Viewport: ${size[2]} (${size[0]}x${size[1]})`, () => {
      before(() => {
        cy.viewport(Number(size[0]), Number(size[1]));
        username = Guid.newGuid().toString();
      });

      it('create account', () => {
        app.visit();
        app.createAccount(username);
        app.logout();
      });

      it('login', () => {
        app.login(username);
        app.closePremiumOverlay();
        app.logout();
      });
    });
  });
});
