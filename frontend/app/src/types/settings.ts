import { z } from 'zod';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type GlobalConfig, type ValidationArgs } from '@vuelidate/core';
import { type MaybeRef } from '@vueuse/shared';

const EvmRpcNode = z.object({
  identifier: z.number(),
  name: z.string().min(1),
  endpoint: z.string(),
  owned: z.boolean(),
  weight: z.preprocess(
    weight => Number.parseFloat(weight as string),
    z.number().nonnegative().max(100)
  ),
  active: z.boolean(),
  blockchain: z.string().min(1)
});

export type EvmRpcNode = z.infer<typeof EvmRpcNode>;

export const EvmRpcNodeList = z.array(EvmRpcNode);

export type EvmRpcNodeList = z.infer<typeof EvmRpcNodeList>;

export const getPlaceholderNode = (chain: Blockchain): EvmRpcNode => ({
  identifier: -1,
  name: '',
  endpoint: '',
  weight: 0,
  active: true,
  owned: true,
  blockchain: chain
});

export type EvmRpcValidation = {
  rules: ValidationArgs;
  state: Record<string, MaybeRef<any>>;
  config?: GlobalConfig;
};
