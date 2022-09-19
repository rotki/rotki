import { z } from 'zod';

export const PeriodicClientQueryResult = z.object({
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
  connectedEthNodes: z.array(z.string())
});

export type PeriodicClientQueryResult = z.infer<
  typeof PeriodicClientQueryResult
>;

export const Messages = z.object({
  warnings: z.array(z.string()),
  errors: z.array(z.string())
});

export type Messages = z.infer<typeof Messages>;
