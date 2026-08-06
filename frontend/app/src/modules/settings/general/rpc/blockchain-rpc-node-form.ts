import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { z, type ZodType } from 'zod';
import { numberSettingField, textSettingField } from '@/modules/settings/controls/setting-field-schemas';

export interface BlockchainRpcNodeFormState {
  active: boolean;
  endpoint: string;
  name: string;
  owned: boolean;
  /** Text, because the slider and the numeric field edit the same value through two controls. */
  weight: string;
}

export interface BlockchainRpcNodeFormMessages {
  endpointRequired: string;
  nameRequired: string;
  weightBetween: string;
  weightRequired: string;
}

export const MIN_WEIGHT = 0;

export const MAX_WEIGHT = 100;

export function toWeight(value?: string): number {
  if (!value)
    return 0;

  const parsed = Number.parseInt(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function stateFromNode(node: BlockchainRpcNode): BlockchainRpcNodeFormState {
  return {
    active: node.active,
    endpoint: node.endpoint,
    name: node.name,
    owned: node.owned,
    weight: node.weight.toString(),
  };
}

/** The form's half of a node, ready to be merged over the one the dialog holds. */
export function toNodeFields(state: BlockchainRpcNodeFormState): Pick<BlockchainRpcNode, 'active' | 'endpoint' | 'name' | 'owned' | 'weight'> {
  return {
    active: state.active,
    endpoint: state.endpoint,
    name: state.name,
    owned: state.owned,
    weight: toWeight(state.weight),
  };
}

/**
 * Etherscan is queried through an api key rather than a url, so it is the one node that is valid
 * without an endpoint. It identifies itself by name, since it has no endpoint to identify it by.
 */
export function isEtherscanNode(state: Pick<BlockchainRpcNodeFormState, 'endpoint' | 'name'>): boolean {
  return !state.endpoint && state.name.includes('etherscan');
}

export function blockchainRpcNodeSchema(messages: BlockchainRpcNodeFormMessages): ZodType {
  return z.object({
    active: z.boolean(),
    // The endpoint rule depends on the name, so it is refined on the object rather than the field.
    endpoint: z.string(),
    name: textSettingField({
      messages: { required: messages.nameRequired },
      required: true,
    }),
    owned: z.boolean(),
    weight: numberSettingField({
      max: MAX_WEIGHT,
      messages: { between: messages.weightBetween, required: messages.weightRequired },
      min: MIN_WEIGHT,
      required: true,
    }),
  }).superRefine((state, ctx) => {
    if (state.endpoint.trim() === '' && !isEtherscanNode(state))
      ctx.addIssue({ code: 'custom', message: messages.endpointRequired, path: ['endpoint'] });
  });
}
