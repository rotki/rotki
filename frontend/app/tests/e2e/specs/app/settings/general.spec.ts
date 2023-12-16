import { GeneralSettingsPage } from '../../../pages/general-settings-page';
import { RotkiApp } from '../../../pages/rotki-app';
import { createUser } from '../../../utils/user';

describe('settings::general', () => {
  let username: string;
  let app: RotkiApp;
  let pageGeneral: GeneralSettingsPage;

  const name = 'local';
  const endpoint = 'http://localhost:9001';

  const settings = {
    floatingPrecision: '4',
    anonymousUsageStatistics: false,
    currency: 'JPY',
    balanceSaveFrequency: '48',
    dateDisplayFormat: '%d-%m-%Y %H:%M:%S %z',
    evmchainsToSkipDetection: ['eth', 'avax', 'optimism', 'polygon_pos', 'arbitrum_one', 'base', 'gnosis', 'scroll'],
    thousandSeparator: ',',
    decimalSeparator: '.',
    currencyLocation: 'after' as 'after' | 'before',
    rpcEndpoint: 'http://localhost:8545',
  };

  before(() => {
    username = createUser();
    app = new RotkiApp();
    pageGeneral = new GeneralSettingsPage();
    app.fasterLogin(username);
    pageGeneral.visit();
  });

  it('change precision & validate UI message', () => {
    pageGeneral.setFloatingPrecision(settings.floatingPrecision);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__floating-precision .details .text-rui-success',
      settings.floatingPrecision,
    );
  });

  it('change anonymous statistics switch & validate UI message', () => {
    pageGeneral.changeAnonymousUsageStatistics();
  });

  it('change main currency and validate UI message', () => {
    pageGeneral.selectCurrency(settings.currency);
    pageGeneral.confirmInlineSuccess('.general-settings__fields__currency-selector .details', settings.currency);
  });

  it('change chains for which to exclude token detection and validate UI message', () => {
    const target = '.general-settings__fields__account-chains-to-skip-detection .details';
    cy.wrap(settings.evmchainsToSkipDetection).each((chain: string) => {
      pageGeneral.selectChainToIgnore(chain);
      pageGeneral.confirmInlineSuccess(
        target,
        'EVM Chains for which to skip automatic token detection saved successfully',
      );
      cy.get(target).should('be.empty');
    });
  });

  it('change balance save frequency and validate UI message', () => {
    pageGeneral.setBalanceSaveFrequency(settings.balanceSaveFrequency);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__balance-save-frequency .details .text-rui-success',
      settings.balanceSaveFrequency,
    );
  });

  it('change date display format and validate UI message', () => {
    pageGeneral.setDateDisplayFormat(settings.dateDisplayFormat);
    pageGeneral.confirmInlineSuccess(
      '.general-settings__fields__date-display-format .details',
      settings.dateDisplayFormat,
    );
  });

  it('verify changed settings', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.verify(settings);
    pageGeneral.confirmRPCmissing(name, endpoint);
  });

  it('add ethereum rpc', () => {
    pageGeneral.confirmRPCmissing(name, endpoint);
    pageGeneral.addEthereumRPC(name, endpoint);
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify changed settings after changing rpc', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.verify(settings);
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify settings persist after re-login', () => {
    app.relogin(username);
    pageGeneral.visit();
    pageGeneral.verify(settings);
  });
});
