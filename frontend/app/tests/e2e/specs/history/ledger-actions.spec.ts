import { Guid } from '../../../common/guid';
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
});
