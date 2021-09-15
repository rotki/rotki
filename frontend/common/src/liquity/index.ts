import { BigNumber } from "bignumber.js";
import { z } from "zod";

const numericString = z.string().transform(arg => new BigNumber(arg));

const AssetValue = z.object({
  asset: z.string().nonempty(),
  amount: numericString,
  usdValue: numericString
})

const Trove = z.object({
  collateral: AssetValue,
  debt: AssetValue,
  collateralizationRatio: numericString.nullable(),
  liquidationPrice: numericString.nullable(),
  active: z.boolean(),
  troveId: z.number()
})

const LiquityBalance = z.object({
  trove: Trove,
  stake: AssetValue.optional()
})

export const LiquityBalances = z.record(LiquityBalance)

export type LiquityBalances = z.infer<typeof LiquityBalances>

const TroveEvent = z.object({
  kind: z.literal('trove'),
  tx: z.string(),
  address: z.string(),
  timestamp: z.number(),
  debtAfter: AssetValue,
  debtDelta: AssetValue,
  collateralDelta: AssetValue,
  troveOperation: z.string()
})

const TroveEvents = z.array(TroveEvent)

const StakeEvent = z.object({
  kind: z.literal('stake'),
  tx: z.string(),
  address: z.string(),
  timestamp: z.number(),
  stakeAfter: AssetValue,
  stakeChange: AssetValue,
  issuanceGain: AssetValue,
  redemptionGain: AssetValue,
  stakeOperation: z.string()
})

const StakeEvents = z.array(StakeEvent)

const LiquityEvent = z.object({
  trove: TroveEvents,
  stake: StakeEvents
});

export const LiquityEvents = z.record(LiquityEvent)

export type LiquityEvents = z.infer<typeof LiquityEvents>