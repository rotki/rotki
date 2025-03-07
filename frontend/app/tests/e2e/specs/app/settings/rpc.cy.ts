import { RotkiApp } from '../../../pages/rotki-app';
import { RpcSettingsPage } from '../../../pages/rpc-settings-page';
import { createUser } from '../../../utils/user';

describe('settings::rpc', () => {
  let username: string;
  let app: RotkiApp;
  let pageGeneral: RpcSettingsPage;

  const name = 'local';
  const endpoint = 'http://localhost:9001';

  before(() => {
    username = createUser();
    app = new RotkiApp();
    pageGeneral = new RpcSettingsPage();
    app.fasterLogin(username);
    pageGeneral.visit();
  });

  it('add ethereum rpc', () => {
    pageGeneral.confirmRPCmissing(name, endpoint);
    pageGeneral.addEthereumRPC(name, endpoint);
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify changed settings after changing rpc', () => {
    pageGeneral.navigateAway();
    pageGeneral.visit();
    pageGeneral.confirmRPCAddition(name, endpoint);
  });

  it('verify settings persist after re-login', () => {
    app.relogin(username);
    pageGeneral.visit();
  });
});
