import { Eth2Validators } from '@rotki/common/lib/staking/eth2';
import { MutationTree } from 'vuex';
import {
  Balances,
  BalanceType,
  BlockchainAssetBalances,
  BtcBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import { BalanceMutations } from '@/store/balances/mutation-types';
import { defaultState } from '@/store/balances/state';
import {
  AccountAssetBalances,
  AssetPrices,
  BalanceState,
  NonFungibleBalances
} from '@/store/balances/types';
import { ExchangeRates } from '@/types/user';

export const mutations: MutationTree<BalanceState> = {
  updateEth(state: BalanceState, payload: BlockchainAssetBalances) {
    state.eth = { ...payload };
  },
  updateEth2(state: BalanceState, payload: BlockchainAssetBalances) {
    state.eth2 = { ...payload };
  },
  updateBtc(state: BalanceState, payload: BtcBalances) {
    state.btc = { ...payload };
  },
  updateBch(state: BalanceState, payload: BtcBalances) {
    state.bch = { ...payload };
  },
  updateKsm(state: BalanceState, payload: BlockchainAssetBalances) {
    state.ksm = { ...payload };
  },
  updateDot(state: BalanceState, payload: BlockchainAssetBalances) {
    state.dot = { ...payload };
  },
  updateAvax(state: BalanceState, payload: BlockchainAssetBalances) {
    state.avax = { ...payload };
  },
  updateTotals(state: BalanceState, payload: Balances) {
    const totals = { ...state.totals, ...payload };

    for (const asset in totals) {
      if (totals[asset].amount.isZero()) delete totals[asset];
    }

    state.totals = totals;
  },
  updateLiabilities(state: BalanceState, payload: Balances) {
    const liabilities = { ...state.liabilities, ...payload };

    for (const asset in liabilities) {
      if (liabilities[asset].amount.isZero()) delete liabilities[asset];
    }

    state.liabilities = liabilities;
  },
  usdToFiatExchangeRates(
    state: BalanceState,
    usdToFiatExchangeRates: ExchangeRates
  ) {
    state.usdToFiatExchangeRates = usdToFiatExchangeRates;
  },
  ethAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.ethAccounts = accounts;
  },
  btcAccounts(state: BalanceState, accounts: BtcAccountData) {
    state.btcAccounts = accounts;
  },
  bchAccounts(state: BalanceState, accounts: BtcAccountData) {
    state.bchAccounts = accounts;
  },
  ksmAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.ksmAccounts = accounts;
  },
  dotAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.dotAccounts = accounts;
  },
  avaxAccounts(state: BalanceState, accounts: GeneralAccountData[]) {
    state.avaxAccounts = accounts;
  },
  eth2Validators(state: BalanceState, eth2Validators: Eth2Validators) {
    state.eth2Validators = eth2Validators;
  },
  manualBalances(
    state: BalanceState,
    manualBalances: ManualBalanceWithValue[]
  ) {
    state.manualBalances = manualBalances.filter(
      x => x.balanceType === BalanceType.ASSET
    );
    state.manualLiabilities = manualBalances.filter(
      x => x.balanceType === BalanceType.LIABILITY
    );
  },
  [BalanceMutations.UPDATE_PRICES](state: BalanceState, prices: AssetPrices) {
    state.prices = prices;
  },
  [BalanceMutations.UPDATE_LOOPRING_BALANCES](
    state: BalanceState,
    balances: AccountAssetBalances
  ) {
    state.loopringBalances = balances;
  },
  [BalanceMutations.UPDATE_NF_BALANCES](
    state: BalanceState,
    balances: NonFungibleBalances
  ) {
    state.nonFungibleBalances = balances;
  },
  reset(state: BalanceState) {
    Object.assign(state, defaultState());
  }
};
