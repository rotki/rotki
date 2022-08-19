export type ExternalTrade = {
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
};

export type ExternalLedgerAction = {
  readonly datetime: string;
  readonly asset: string;
  readonly asset_id: string;
  readonly rate_asset: string;
  readonly rate_asset_id: string;
  readonly rate: string;
  readonly location: string;
  readonly amount: string;
  readonly action_type: string;
  readonly link: string;
  readonly notes: string;
};

declare global {
  namespace Cypress {
    interface Chainable {
      logout: () => void;
      updateAssets: () => void;
      disableModules: () => void;
      createAccount: (username: string, password?: string) => Chainable;
      addExternalTrade: (trade: ExternalTrade) => Chainable;
      addLedgerAction: (action: ExternalLedgerAction) => Chainable;
      addEtherscanKey: (key: string) => Chainable;
    }
  }
}
