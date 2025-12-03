import { EvmSettingsPage } from '../../../pages/evm-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { createUser } from '../../../utils/user';

describe('settings::evm', () => {
  let username: string;
  let app: RotkiApp;
  let page: EvmSettingsPage;

  const testChain = 'eth';
  const evmchainsToSkipDetection = ['eth', 'avax', 'optimism', 'polygon_pos', 'arbitrum_one', 'base', 'gnosis', 'scroll'];

  before(() => {
    username = createUser();
    app = new RotkiApp();
    page = new EvmSettingsPage();
    app.fasterLogin(username);
    page.visit();
  });

  it('change chains for which to exclude token detection and validate UI message', () => {
    evmchainsToSkipDetection.forEach((chain: string) => {
      page.selectChainToIgnore(chain);
    });

    cy.get('[data-cy=chains-to-skip-detection]').type('{esc}');
    page.verifySkipped(evmchainsToSkipDetection);
  });

  it('displays indexer order setting section', () => {
    page.getIndexerOrderSection().should('be.visible');
  });

  it('has default tab selected by default', () => {
    page.verifyTabExists('default');
  });

  it('can add and remove a chain-specific indexer order', () => {
    // First ensure the chain is not configured by removing it if it exists
    page.isAddChainButtonDisabled().then((isDisabled) => {
      if (isDisabled) {
        // All chains are configured, remove one first
        page.removeChain(testChain);
        page.verifyTabNotExists(testChain);
      }
    });

    // Now add the chain
    page.addChain(testChain);
    page.verifyTabExists(testChain);

    // Switch between tabs
    page.selectTab('default');
    page.selectTab(testChain);

    // Remove the chain
    page.removeChain(testChain);
    page.verifyTabNotExists(testChain);
  });

  it('verify settings persist after navigation', () => {
    page.addChain(testChain);
    page.verifyTabExists(testChain);
    page.navigateAway();
    page.visit();
    page.verifyTabExists(testChain);
  });

  it('verify settings persist after re-login', () => {
    app.relogin(username);
    page.visit();
    page.verifyTabExists(testChain);
    page.verifySkipped(evmchainsToSkipDetection);
  });
});
