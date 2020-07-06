import { default as BigNumber } from 'bignumber.js';
import {
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails,
  ApiMakerDAOVaultEvent
} from '@/services/defi/types';
import {
  DSRBalances,
  DSRHistory,
  DSRMovement,
  MakerDAOVault,
  MakerDAOVaultDetails,
  MakerDAOVaultEvent
} from '@/store/defi/types';
import { bigNumberify } from '@/utils/bignumbers';

export function convertDSRBalances({
  balances,
  current_dsr
}: ApiDSRBalances): DSRBalances {
  const data: {
    [account: string]: { amount: BigNumber; usdValue: BigNumber };
  } = {};
  for (const account of Object.keys(balances)) {
    data[account] = {
      amount: bigNumberify(balances[account].amount),
      usdValue: bigNumberify(balances[account].usd_value)
    };
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
      gainSoFarUsdValue: BigNumber;
    };
  } = {};
  for (const account of Object.keys(history)) {
    const {
      gain_so_far: accountGain,
      gain_so_far_usd_value: accountGainUsdValue,
      movements
    } = history[account];
    data[account] = {
      gainSoFar: bigNumberify(accountGain),
      gainSoFarUsdValue: bigNumberify(accountGainUsdValue),
      movements: movements.map(
        ({
          amount,
          amount_usd_value,
          block_number,
          gain_so_far: gain_so_far,
          gain_so_far_usd_value: gain_so_far_usd_value,
          movement_type,
          timestamp,
          tx_hash
        }) => ({
          movementType: movement_type,
          gainSoFar: bigNumberify(gain_so_far),
          gainSoFarUsdValue: bigNumberify(gain_so_far_usd_value),
          amount: bigNumberify(amount),
          amountUsdValue: bigNumberify(amount_usd_value),
          blockNumber: block_number,
          timestamp,
          txHash: tx_hash
        })
      )
    };
  }
  return data;
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
