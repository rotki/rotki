import type { Blockchain } from '@rotki/common';

export interface FieldMessage {
  target: string;
  mustInclude: string;
  messageContains?: string;
}

export interface FixtureBlockchainAccount {
  readonly blockchain: Blockchain;
  readonly inputMode: string;
  readonly chainName: string;
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

declare global {
  namespace Cypress {
    interface Chainable {
      logout: () => void;
      updateAssets: () => void;
      disableModules: () => void;
      confirmFieldMessage: (params: FieldMessage) => void;
      createAccount: (username: string, password?: string) => Chainable;
      addEtherscanKey: (key: string) => Chainable;
      assertNoRunningTasks: () => Chainable;
      scrollElemToTop: (target: string) => void;
    }
  }
}
