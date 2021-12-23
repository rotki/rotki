import { z } from 'zod';
import { setupTransformer } from '@/services/axios-tranformers';

export const tradeNumericKeys = ['fee', 'amount', 'rate'];
export const movementNumericKeys = ['fee', 'amount'];
export const transactionNumericKeys = ['value', 'gas', 'gas_price', 'gas_used'];

export const IgnoredActions = z
  .object({
    'ledger action': z.array(z.string()).optional(),
    'asset movement': z.array(z.string()).optional(),
    'ethereum transaction': z.array(z.string()).optional(),
    trade: z.array(z.string()).optional()
  })
  .transform(arg => {
    const ignoredActions: {
      ledgerActions?: string[];
      assetMovements?: string[];
      ethereumTransactions?: string[];
      trades?: string[];
    } = {
      ledgerActions: arg['ledger action'],
      assetMovements: arg['asset movement'],
      ethereumTransactions: arg['ethereum transaction'],
      trades: arg.trade
    };
    return ignoredActions;
  });

export type IgnoredActions = z.infer<typeof IgnoredActions>;

export const movementAxiosTransformer = setupTransformer(movementNumericKeys);
