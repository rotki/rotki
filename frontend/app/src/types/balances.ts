import { z } from 'zod';

export type Eth2Validator = {
  readonly validatorIndex?: string;
  readonly publicKey?: string;
};

const Validator = z.object({
  validatorIndex: z.number(),
  publicKey: z.string()
});

export const Eth2Validators = z.array(Validator);

export type Eth2Validators = z.infer<typeof Eth2Validators>;
