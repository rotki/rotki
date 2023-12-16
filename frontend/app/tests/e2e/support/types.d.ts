export interface ExternalTrade {
  readonly time: string;
  readonly base: string;
  readonly base_id: string;
  readonly quote: string;
  readonly quote_id: string;
  readonly trade_type: 'buy' | 'sell';
  readonly amount: string;
  readonly rate: string;
  readonly quote_amount: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly fee_id: string;
  readonly link: string;
  readonly notes: string;
  readonly location?: string;
}

export interface FieldMessage {
  target: string;
  mustInclude: string;
  messageContains?: string;
}

declare global {
  namespace Cypress {
    interface Chainable {
      logout: () => void;
      updateAssets: () => void;
      disableModules: () => void;
      confirmFieldMessage: (params: FieldMessage) => void;
      createAccount: (username: string, password?: string) => Chainable;
      addExternalTrade: (trade: ExternalTrade) => Chainable;
      addEtherscanKey: (key: string) => Chainable;
      assertNoRunningTasks: () => Chainable;
      scrollElemToTop: (target: string) => void;
    }
  }
}
