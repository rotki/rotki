export type ExternalTrade = {
  readonly time: string;
  readonly base: string;
  readonly base_id: string;
  readonly quote: string;
  readonly quote_id: string;
  readonly trade_type: 'buy' | 'sell';
  readonly amount: string;
  readonly rate: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly fee_id: string;
  readonly link: string;
  readonly notes: string;
};

declare global {
  namespace Cypress {
    interface Chainable {
      logout: () => void;
      updateAssets: () => void;
    }
  }
}
