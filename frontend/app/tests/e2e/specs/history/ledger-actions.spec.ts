import { Guid } from '../../common/guid';
import { HistoryPage } from '../../pages/history-page';
import { LedgerActionPage } from '../../pages/history-page/ledger-action-page';
import { RotkiApp } from '../../pages/rotki-app';
import { type ExternalLedgerAction } from '../../support/types';

describe('ledger actions history', () => {
  let username: string;
  let app: RotkiApp;
  let page: HistoryPage;
  let ledgerActionPage: LedgerActionPage;
  let externalLedgerActions: ExternalLedgerAction[];

  beforeEach(() => {
    username = Guid.newGuid().toString();
    app = new RotkiApp();
    page = new HistoryPage();
    ledgerActionPage = new LedgerActionPage();
    app.fasterLogin(username);
    page.visit();
    cy.fixture('history/ledger-actions').then(ledgerAction => {
      externalLedgerActions = ledgerAction;
    });
  });

  afterEach(() => {
    app.fasterLogout();
  });

  it('add two ledger actions', () => {
    ledgerActionPage.visit();
    ledgerActionPage.addLedgerAction(externalLedgerActions[0]);
    ledgerActionPage.addLedgerAction(externalLedgerActions[1]);
    ledgerActionPage.visibleEntries(2);
    ledgerActionPage.ledgerActionIsVisible(0, externalLedgerActions[0]);
    ledgerActionPage.ledgerActionIsVisible(1, externalLedgerActions[1]);
  });

  it('edit ledger action', () => {
    cy.addLedgerAction(externalLedgerActions[0]);
    ledgerActionPage.visit();
    ledgerActionPage.visibleEntries(1);
    ledgerActionPage.editTrade(0, '123.2');
    ledgerActionPage.ledgerActionIsVisible(0, {
      ...externalLedgerActions[0],
      amount: '123.2'
    });
  });

  it('delete ledger action', () => {
    cy.addLedgerAction(externalLedgerActions[0]);
    cy.addLedgerAction(externalLedgerActions[1]);
    ledgerActionPage.visit();
    ledgerActionPage.visibleEntries(2);
    ledgerActionPage.deleteLedgerAction(0);
    ledgerActionPage.confirmDelete();
    ledgerActionPage.visibleEntries(1);
    ledgerActionPage.ledgerActionIsVisible(0, externalLedgerActions[1]);
  });

  it('filter and pagination', () => {
    for (let i = 0; i < 6; i++) {
      cy.addLedgerAction(externalLedgerActions[0]);
      cy.addLedgerAction(externalLedgerActions[1]);
    }

    for (let i = 0; i < 6; i++) {
      cy.addLedgerAction({ ...externalLedgerActions[0], location: 'equities' });
      cy.addLedgerAction({ ...externalLedgerActions[1], location: 'equities' });
    }

    ledgerActionPage.visit();

    // after addition, should have 24 entries on table
    ledgerActionPage.visibleEntries(10);
    ledgerActionPage.totalEntries(24);
    ledgerActionPage.shouldBeOnPage(1);

    // go to page 2
    ledgerActionPage.nextPage();
    ledgerActionPage.shouldBeOnPage(2);
    app.shouldHaveQueryParam('page', '2');
    app.shouldHaveQueryParams('sortBy', ['timestamp']);

    // apply filter location
    ledgerActionPage.filterLedgerActions('location: kraken');
    ledgerActionPage.visibleEntries(10);
    ledgerActionPage.totalEntries(12);
    ledgerActionPage.shouldBeOnPage(1);
    app.shouldHaveQueryParam('page', '1');

    // go to page 2
    ledgerActionPage.nextPage();
    ledgerActionPage.shouldBeOnPage(2);
    ledgerActionPage.visibleEntries(2);
    app.shouldHaveQueryParam('page', '2');

    // history back, should go back to page 1
    cy.go(-1);
    ledgerActionPage.shouldBeOnPage(1);
    ledgerActionPage.visibleEntries(10);
    app.shouldHaveQueryParam('page', '1');

    // history back, should remove filter
    cy.go(-1);
    ledgerActionPage.totalEntries(24);
    ledgerActionPage.shouldBeOnPage(1);

    // history forward, should reapply location filter
    cy.go(1);
    ledgerActionPage.totalEntries(12);
    app.shouldHaveQueryParam('page', '1');
  });
});
