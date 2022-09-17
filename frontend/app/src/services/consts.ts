import { setupTransformer } from '@/services/axios-tranformers';

/**
 * @deprecated
 * use zod schema parsing
 */
export const balanceKeys = ['amount', 'usd_value'];

export const basicAxiosTransformer = setupTransformer([]);
export const balanceAxiosTransformer = setupTransformer(balanceKeys);
