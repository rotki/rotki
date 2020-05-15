import { default as BigNumber } from 'bignumber.js';
import {
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiManualBalances,
  ApiVaultDetails,
  ApiVaultEvent,
  SupportedAssets
} from '@/services/types-api';
import {
  DSRBalances,
  DSRHistory,
  DSRMovement,
  MakerDAOVault,
  ManualBalance,
  SupportedAsset,
  VaultDetails,
  VaultEvent
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
    name: vault.name,
    collateralAsset: vault.collateral_asset,
    collateralAmount: bigNumberify(vault.collateral_amount),
    debtValue: bigNumberify(vault.debt_value),
    liquidationRatio: vault.liquidation_ratio,
    collateralizationRatio:
      vault.collateralization_ratio === null
        ? undefined
        : vault.collateralization_ratio
  }));
}

function convertVaultEvents(apiVaultEvents: ApiVaultEvent[]): VaultEvent[] {
  return apiVaultEvents.map(event => ({
    eventType: event.event_type,
    amount: new BigNumber(event.amount),
    timestamp: event.timestamp,
    txHash: event.tx_hash
  }));
}

export function convertVaultDetails(
  apiVaultDetails: ApiVaultDetails[]
): VaultDetails[] {
  return apiVaultDetails.map(details => ({
    identifier: details.identifier,
    liquidationPrice: new BigNumber(details.liquidation_price),
    collateralUsdValue: new BigNumber(details.collateral_usd_value),
    creationTs: details.creation_ts,
    totalInterestOwed: new BigNumber(details.total_interest_owed),
    events: convertVaultEvents(details.events)
  }));
}
