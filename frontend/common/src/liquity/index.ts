import { z } from "zod";
import { AssetBalance, NumericString } from "../index";

const Trove = z.object({
  collateral: AssetBalance,
  debt: AssetBalance,
  collateralizationRatio: NumericString.nullable(),
  liquidationPrice: NumericString.nullable(),
  active: z.boolean(),
  troveId: z.number()
})

const LiquityBalance = z.object({
  trove: Trove,
  stake: AssetBalance.optional()
})

export type LiquityBalance = z.infer<typeof LiquityBalance>

export const LiquityBalances = z.record(LiquityBalance)

export type LiquityBalances = z.infer<typeof LiquityBalances>

const TroveEvent = z.object({
  kind: z.literal('trove'),
  sequenceNumber: z.string(),
  tx: z.string(),
  address: z.string(),
  timestamp: z.number(),
  debtAfter: AssetBalance,
  debtDelta: AssetBalance,
  collateralAfter: AssetBalance,
  collateralDelta: AssetBalance,
  troveOperation: z.string()
})

export type TroveEvent = z.infer<typeof TroveEvent>

const TroveEvents = z.array(TroveEvent)

const StakeEvent = z.object({
  kind: z.literal('stake'),
  tx: z.string(),
  address: z.string(),
  timestamp: z.number(),
  stakeAfter: AssetBalance,
  stakeChange: AssetBalance,
  issuanceGain: AssetBalance,
  redemptionGain: AssetBalance,
  stakeOperation: z.string()
})

export type StakeEvent = z.infer<typeof StakeEvent>

const StakeEvents = z.array(StakeEvent)

const LiquityAccountEvents = z.object({
  trove: TroveEvents,
  stake: StakeEvents.optional()
});

export type LiquityAccountEvents = z.infer<typeof LiquityAccountEvents>

export const LiquityEvents = z.record(LiquityAccountEvents)

export type LiquityEvents = z.infer<typeof LiquityEvents>