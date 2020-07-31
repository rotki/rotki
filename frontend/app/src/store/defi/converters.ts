import { default as BigNumber } from 'bignumber.js';
import { ApiBalance, Balance } from '@/model/blockchain-balances';
import {
  ApiAaveBalances,
  ApiAaveBorrowingAsset,
  ApiAaveHistory,
  ApiAaveHistoryEvents,
  ApiAaveLendingAsset,
  ApiAllDefiProtocols,
  ApiDefiAsset,
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails,
  ApiMakerDAOVaultEvent
} from '@/services/defi/types';
import {
  AaveBalances,
  AaveBorrowing,
  AaveBorrowingAsset,
  AaveHistory,
  AaveHistoryEvents,
  AaveHistoryTotalEarned,
  AaveLending,
  AaveLendingAsset,
  AllDefiProtocols,
  DefiAsset,
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
      gain_so_far: { amount: accountGain, usd_value: accountGainUsdValue },
      movements
    } = history[account];
    data[account] = {
      gainSoFar: bigNumberify(accountGain),
      gainSoFarUsdValue: bigNumberify(accountGainUsdValue),
      movements: movements.map(
        ({
          value,
          block_number,
          gain_so_far: gain_so_far,
          movement_type,
          timestamp,
          tx_hash
        }) => ({
          movementType: movement_type,
          gainSoFar: {
            amount: bigNumberify(gain_so_far.amount),
            usdValue: bigNumberify(gain_so_far.usd_value)
          },
          balance: {
            amount: bigNumberify(value.amount),
            usdValue: bigNumberify(value.usd_value)
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
    identifier: vault.identifier.toString(),
    collateralType: vault.collateral_type,
    protocol: 'makerdao',
    owner: vault.owner,
    collateral: {
      asset: vault.collateral_asset,
      amount: bigNumberify(vault.collateral.amount),
      usdValue: bigNumberify(vault.collateral.usd_value)
    },
    debt: {
      amount: bigNumberify(vault.debt.amount),
      usdValue: bigNumberify(vault.debt.usd_value)
    },
    liquidationRatio: vault.liquidation_ratio,
    liquidationPrice: bigNumberify(vault.liquidation_price),
    collateralizationRatio: vault.collateralization_ratio ?? undefined,
    stabilityFee: vault.stability_fee
  }));
}

function convertVaultEvents(
  apiVaultEvents: ApiMakerDAOVaultEvent[]
): MakerDAOVaultEvent[] {
  return apiVaultEvents.map(event => ({
    eventType: event.event_type,
    amount: bigNumberify(event.value.amount),
    amountUsdValue: bigNumberify(event.value.usd_value),
    timestamp: event.timestamp,
    txHash: event.tx_hash
  }));
}

export function convertVaultDetails(
  apiVaultDetails: ApiMakerDAOVaultDetails[]
): MakerDAOVaultDetails[] {
  return apiVaultDetails.map(details => ({
    identifier: details.identifier.toString(),
    creationTs: details.creation_ts,
    totalInterestOwed: bigNumberify(details.total_interest_owed),
    totalLiquidated: {
      amount: bigNumberify(details.total_liquidated.amount),
      usdValue: bigNumberify(details.total_liquidated.usd_value)
    },
    events: convertVaultEvents(details.events)
  }));
}

function convertBalance({ amount, usd_value }: ApiBalance): Balance {
  return {
    amount: bigNumberify(amount),
    usdValue: bigNumberify(usd_value)
  };
}

const convertAaveBorrowingAsset = ({
  balance,
  stable_apr,
  variable_apr
}: ApiAaveBorrowingAsset): AaveBorrowingAsset => ({
  stableApr: stable_apr,
  variableApr: variable_apr,
  balance: convertBalance(balance)
});

const convertAaveLendingAsset = ({
  balance,
  apy
}: ApiAaveLendingAsset): AaveLendingAsset => ({
  apy: apy,
  balance: convertBalance(balance)
});

export function convertAaveBalances(
  apiBalances: ApiAaveBalances
): AaveBalances {
  const aaveBalances: Writeable<AaveBalances> = {};
  for (const address of Object.keys(apiBalances)) {
    const convertedBorrowing: Writeable<AaveBorrowing> = {};
    const convertedLending: Writeable<AaveLending> = {};
    const { borrowing, lending } = apiBalances[address];

    for (const asset of Object.keys(borrowing)) {
      convertedBorrowing[asset] = convertAaveBorrowingAsset(borrowing[asset]);
    }
    for (const asset of Object.keys(lending)) {
      convertedLending[asset] = convertAaveLendingAsset(lending[asset]);
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

function convertDefiAsset(apiAsset: ApiDefiAsset): DefiAsset {
  return {
    balance: convertBalance(apiAsset.balance),
    tokenAddress: apiAsset.token_address,
    tokenName: apiAsset.token_name,
    tokenSymbol: apiAsset.token_symbol
  };
}

export function convertAllDefiProtocols(
  allProtocols: ApiAllDefiProtocols
): AllDefiProtocols {
  const data: Writeable<AllDefiProtocols> = {};
  for (const address of Object.keys(allProtocols)) {
    data[address] = allProtocols[address].map(value => ({
      protocol: { ...value.protocol },
      balanceType: value.balance_type,
      baseBalance: convertDefiAsset(value.base_balance),
      underlyingBalances: value.underlying_balances.map(convertDefiAsset)
    }));
  }

  return data;
}
