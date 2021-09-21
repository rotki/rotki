import { z } from "zod";
import { Balance, NumericString } from "../index";

const AssetEntry = z.object({
  asset: z.string().nonempty(),
});

const AssetValue = Balance.merge(AssetEntry)

export type AssetValue = z.infer<typeof AssetValue>

const Trove = z.object({
  collateral: AssetValue,
  debt: AssetValue,
  collateralizationRatio: NumericString.nullable(),
  liquidationPrice: NumericString.nullable(),
  active: z.boolean(),
  troveId: z.number()
})

const LiquityBalance = z.object({
  trove: Trove,
  stake: AssetValue.optional()
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
  debtAfter: AssetValue,
  debtDelta: AssetValue,
  collateralAfter: AssetValue,
  collateralDelta: AssetValue,
  troveOperation: z.string()
})

export type TroveEvent = z.infer<typeof TroveEvent>

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

export type StakeEvent = z.infer<typeof StakeEvent>

const StakeEvents = z.array(StakeEvent)

const LiquityAccountEvents = z.object({
  trove: TroveEvents,
  stake: StakeEvents.optional()
});

export type LiquityAccountEvents = z.infer<typeof LiquityAccountEvents>

export const LiquityEvents = z.record(LiquityAccountEvents)

export type LiquityEvents = z.infer<typeof LiquityEvents>