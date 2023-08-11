import { RotkiApp } from '../rotki-app';

export class HistoryPage {
  visit(submenu: string) {
    RotkiApp.navigateTo('history', submenu);
  }
}
