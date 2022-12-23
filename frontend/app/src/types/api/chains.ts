import { z } from 'zod';

const ChainInfo = z.object({
  name: z.string(),
  type: z.string()
});

export const SupportedChains = z.array(ChainInfo);

export type SupportedChains = z.infer<typeof SupportedChains>;
