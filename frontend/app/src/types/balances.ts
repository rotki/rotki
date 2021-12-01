import { z } from 'zod';

export type Eth2Validator = {
  readonly validatorIndex?: string;
  readonly publicKey?: string;
};

const Validator = z.object({
  validatorIndex: z.number(),
  publicKey: z.string()
});

export type Eth2ValidatorEntry = z.infer<typeof Validator>;

export const Eth2Validators = z.object({
  entries: z.array(Validator),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1)
});

export type Eth2Validators = z.infer<typeof Eth2Validators>;
