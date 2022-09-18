import { z } from 'zod';

export const IgnoredActions = z
  .object({
    ledger_action: z.array(z.string()).optional(),
    asset_movement: z.array(z.string()).optional(),
    ethereum_transaction: z.array(z.string()).optional(),
    trade: z.array(z.string()).optional()
  })
  .transform(arg => {
    const ignoredActions: {
      ledgerActions?: string[];
      assetMovements?: string[];
      ethereumTransactions?: string[];
      trades?: string[];
    } = {
      ledgerActions: arg['ledger_action'],
      assetMovements: arg['asset_movement'],
      ethereumTransactions: arg['ethereum_transaction'],
      trades: arg.trade
    };
    return ignoredActions;
  });
export type IgnoredActions = z.infer<typeof IgnoredActions>;
