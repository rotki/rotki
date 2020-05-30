import { default as BigNumber } from 'bignumber.js';
import {
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiManualBalances,
  ApiMakerDAOVaultDetails,
  ApiMakerDAOVaultEvent,
  SupportedAssets
} from '@/services/types-api';
import {
  DSRBalances,
  DSRHistory,
  DSRMovement,
  MakerDAOVault,
  ManualBalance,
  SupportedAsset,
  MakerDAOVaultDetails,
  MakerDAOVaultEvent
} from '@/services/types-model';
import { bigNumberify } from '@/utils/bignumbers';

export function convertDSRBalances({
  balances,
  current_dsr
}: ApiDSRBalances): DSRBalances {
  const data: { [account: string]: BigNumber } = {};
  for (const account of Object.keys(balances)) {
    data[account] = bigNumberify(balances[account]);
  }
  return {
    currentDSR: bigNumberify(current_dsr),
    balances: data
  };
}

export function convertDSRHistory(history: ApiDSRHistory): DSRHistory {
  const data: {
    [address: string]: {
      movements: DSRMovement[];
      gainSoFar: BigNumber;
    };
  } = {};
  for (const account of Object.keys(history)) {
    const { gain_so_far: accountGain, movements } = history[account];
    data[account] = {
      gainSoFar: bigNumberify(accountGain),
      movements: movements.map(
        ({
          amount,
          block_number,
          gain_so_far: gain_so_far,
          movement_type,
          timestamp
        }) => ({
          movementType: movement_type,
          gainSoFar: bigNumberify(gain_so_far),
          amount: bigNumberify(amount),
          blockNumber: block_number,
          timestamp
        })
      )
    };
  }
  return data;
}

export function convertManualBalances(
  manualBalances: ApiManualBalances
): ManualBalance[] {
  return manualBalances.balances.map(value => ({
    amount: bigNumberify(value.amount),
    asset: value.asset,
    label: value.label,
    location: value.location,
    tags: value.tags,
    usdValue: bigNumberify(value.usd_value)
  }));
}

export function convertSupportedAssets(
  supportedAssets: SupportedAssets
): SupportedAsset[] {
  return Object.keys(supportedAssets).map(key => ({
    key,
    ...supportedAssets[key]
  }));
}

export function convertMakerDAOVaults(
  vaults: ApiMakerDAOVault[]
): MakerDAOVault[] {
  return vaults.map(vault => ({
    identifier: vault.identifier,
    collateralType: vault.collateral_type,
    owner: vault.owner,
    collateralAsset: vault.collateral_asset,
    collateralAmount: bigNumberify(vault.collateral_amount),
    debtValue: bigNumberify(vault.debt_value),
    liquidationRatio: vault.liquidation_ratio,
    liquidationPrice: bigNumberify(vault.liquidation_price),
    collateralizationRatio: vault.collateralization_ratio ?? undefined,
    collateralUsdValue: bigNumberify(vault.collateral_usd_value),
    stabilityFee: vault.stability_fee
  }));
}

function convertVaultEvents(
  apiVaultEvents: ApiMakerDAOVaultEvent[]
): MakerDAOVaultEvent[] {
  return apiVaultEvents.map(event => ({
    eventType: event.event_type,
    amount: bigNumberify(event.amount),
    amountUsdValue: bigNumberify(event.amount_usd_value),
    timestamp: event.timestamp,
    txHash: event.tx_hash
  }));
}

export function convertVaultDetails(
  apiVaultDetails: ApiMakerDAOVaultDetails[]
): MakerDAOVaultDetails[] {
  return apiVaultDetails.map(details => ({
    identifier: details.identifier,
    creationTs: details.creation_ts,
    totalInterestOwed: bigNumberify(details.total_interest_owed),
    totalLiquidatedAmount: bigNumberify(details.total_liquidated_amount),
    totalLiquidatedUsd: bigNumberify(details.total_liquidated_usd),
    events: convertVaultEvents(details.events)
  }));
}
