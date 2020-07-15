import { default as BigNumber } from 'bignumber.js';
import { ApiBalance, Balance } from '@/model/blockchain-balances';
import {
  ApiAaveAsset,
  ApiAaveBalances,
  ApiAaveHistory,
  ApiAaveHistoryEvents,
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails,
  ApiMakerDAOVaultEvent
} from '@/services/defi/types';
import {
  AaveBorrowingAsset,
  AaveLendingAsset,
  AaveBalances,
  AaveBorrowing,
  AaveHistory,
  AaveHistoryEvents,
  AaveHistoryTotalEarned,
  AaveLending,
  DSRBalances,
  DSRHistory,
  DSRMovement,
  MakerDAOVault,
  MakerDAOVaultDetails,
  MakerDAOVaultEvent
} from '@/store/defi/types';
import { Writeable } from '@/types';
import { bigNumberify } from '@/utils/bignumbers';

export function convertDSRBalances({
  balances,
  current_dsr
}: ApiDSRBalances): DSRBalances {
  const data: {
    [account: string]: { amount: BigNumber; usdValue: BigNumber };
  } = {};
  for (const account of Object.keys(balances)) {
    data[account] = convertBalance(balances[account]);
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
          gainSoFar: {
            amount: bigNumberify(gain_so_far),
            usdValue: bigNumberify(gain_so_far_usd_value)
          },
          balance: {
            amount: bigNumberify(amount),
            usdValue: bigNumberify(amount_usd_value)
          },
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

function convertBalance({ amount, usd_value }: ApiBalance): Balance {
  return {
    amount: bigNumberify(amount),
    usdValue: bigNumberify(usd_value)
  };
}

function convertAaveAsset<T extends AaveLendingAsset | AaveBorrowingAsset>({
  apy,
  stable_apy,
  variable_apy,
  balance: apiBalance
}: ApiAaveAsset): T {
  const balance = convertBalance(apiBalance);
  if (apy) {
    return {
      apy,
      balance
    } as T;
  }

  return {
    stableApy: stable_apy,
    variableApy: variable_apy,
    balance
  } as T;
}

export function convertAaveBalances(
  apiBalances: ApiAaveBalances
): AaveBalances {
  const aaveBalances: Writeable<AaveBalances> = {};
  for (const address of Object.keys(apiBalances)) {
    const convertedBorrowing: Writeable<AaveBorrowing> = {};
    const convertedLending: Writeable<AaveLending> = {};
    const { borrowing, lending } = apiBalances[address];
    for (const asset of Object.keys(borrowing)) {
      convertedBorrowing[asset] = convertAaveAsset(borrowing[asset]);
    }
    for (const asset of Object.keys(lending)) {
      convertedLending[asset] = convertAaveAsset(lending[asset]);
    }
    aaveBalances[address] = {
      lending: convertedLending,
      borrowing: convertedBorrowing
    };
  }
  return aaveBalances;
}

function convertAaveEvents(
  events: ApiAaveHistoryEvents[]
): AaveHistoryEvents[] {
  return events.map(event => ({
    eventType: event.event_type,
    asset: event.asset,
    value: convertBalance(event.value),
    blockNumber: event.block_number,
    timestamp: event.timestamp,
    txHash: event.tx_hash
  }));
}

export function convertAaveHistory(apiHistory: ApiAaveHistory): AaveHistory {
  const aaveHistory: Writeable<AaveHistory> = {};
  for (const address of Object.keys(apiHistory)) {
    const totalEarned: Writeable<AaveHistoryTotalEarned> = {};
    const { events, total_earned } = apiHistory[address];

    for (const asset of Object.keys(total_earned)) {
      totalEarned[asset] = convertBalance(total_earned[asset]);
    }

    aaveHistory[address] = {
      events: convertAaveEvents(events),
      totalEarned
    };
  }

  return aaveHistory;
}
