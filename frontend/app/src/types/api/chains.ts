import { z } from 'zod';
import { EvmChainEnum } from '@rotki/common/lib/data';

export const ChainInfo = z.object({
  name: z.string(),
  type: z.string(),
  evmChainName: EvmChainEnum.nullish()
});

export type ChainInfo = z.infer<typeof ChainInfo>;

export const SupportedChains = z.array(ChainInfo);

export type SupportedChains = z.infer<typeof SupportedChains>;
