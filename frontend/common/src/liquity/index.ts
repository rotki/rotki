import { z } from "zod";
import { AssetBalance, NumericString } from "../index";

const LiquityBalance = z.object({
  collateral: AssetBalance,
  debt: AssetBalance,
  collateralizationRatio: NumericString.nullable(),
  liquidationPrice: NumericString.nullable(),
  active: z.boolean(),
  troveId: z.number()
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

export const TroveEvents = z.record(z.array(TroveEvent))

export type TroveEvents = z.infer<typeof TroveEvents>

export const LiquityStaking = z.record(AssetBalance)

export type LiquityStaking = z.infer<typeof LiquityStaking>

const LiquityStakingEvent = z.object({
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

export type LiquityStakingEvent = z.infer<typeof LiquityStakingEvent>

export const LiquityStakingEvents = z.record(z.array(LiquityStakingEvent))

export type LiquityStakingEvents = z.infer<typeof LiquityStakingEvents>

