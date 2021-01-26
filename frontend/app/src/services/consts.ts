import { setupTransformer } from '@/services/axios-tranformers';

export const balanceKeys = ['amount', 'usd_value'];

export const basicAxiosTransformer = setupTransformer([]);
export const balanceAxiosTransformer = setupTransformer(balanceKeys);
