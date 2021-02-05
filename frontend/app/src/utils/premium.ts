import Chart from 'chart.js';
import moment from 'moment';
import Vue, { VueConstructor } from 'vue';
import Vuex from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { TIME_UNIT_DAY } from '@/components/dashboard/const';
import { TimeUnit } from '@/components/dashboard/types';
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetMovementDisplay from '@/components/display/AssetMovementDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import EventTypeDisplay from '@/components/display/EventTypeDisplay.vue';
import UniswapPoolAsset from '@/components/display/icons/UniswapPoolAsset.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import PremiumLoadingFailed from '@/components/display/PremiumLoadingFailed.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import HashLink from '@/components/helper/HashLink.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { DebugSettings, ExposedUtilities } from '@/electron-main/ipc';
import { api } from '@/services/rotkehlchen-api';

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.Vue.use(Vuex);
  window.moment = moment;
  window.rotki = {
    useHostComponents: true,
    version: 8,
    utils: {
      date: {
        epoch(): number {
          return moment().unix();
        },
        format(date: string, oldFormat: string, newFormat: string): string {
          return moment(date, oldFormat).format(newFormat);
        },
        now(format: string): string {
          return moment().format(format);
        },
        epochToFormat(epoch: number, format: string): string {
          return moment(epoch * 1000).format(format);
        },
        dateToEpoch(date: string, format: string): number {
          return moment(date, format).unix();
        },
        epochStartSubtract(amount: number, unit: TimeUnit): number {
          return moment().subtract(amount, unit).startOf(TIME_UNIT_DAY).unix();
        }
      }
    }
  };
  // Globally registered components are also provided to the premium components.
  Vue.component('AmountDisplay', AmountDisplay);
  // version: 1
  Vue.component('HashLink', HashLink);
  Vue.component('AssetDetails', AssetDetails);
  Vue.component('DefiProtocolIcon', DefiProtocolIcon);
  // version: 2
  Vue.component('AssetMovementDisplay', AssetMovementDisplay);
  Vue.component('EventTypeDisplay', EventTypeDisplay);
  Vue.component('CryptoIcon', CryptoIcon);
  Vue.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  Vue.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  Vue.component('BlockchainAccountSelector', BlockchainAccountSelector);
  Vue.component('DateDisplay', DateDisplay);
  Vue.component('LocationDisplay', LocationDisplay);
  Vue.component('RefreshHeader', RefreshHeader);
  Vue.component('UniswapPoolAsset', UniswapPoolAsset);
  // version 5
  Vue.component('AssetSelect', AssetSelect);
  // version 6
  Vue.component('DateTimePicker', DateTimePicker);
  // version 8
  Vue.component('CardTitle', CardTitle);
};

function findComponents(): string[] {
  return Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents')
  );
}

if (process.env.NODE_ENV === 'development') {
  // @ts-ignore
  findComponents().forEach(component => (window[component] = undefined));
}

async function loadComponents(): Promise<string[]> {
  // eslint-disable-next-line no-async-promise-executor
  return new Promise(async (resolve, reject) => {
    let components = findComponents();
    if (components.length > 0) {
      resolve(components);
      return;
    }

    const result = await api.queryStatisticsRenderer();
    const script = document.createElement('script');
    script.text = result;
    document.head.appendChild(script);

    components = findComponents();

    if (components.length === 0) {
      reject(new Error('There was no component loaded'));
      return;
    }

    script.addEventListener('error', reject);
    resolve(components);
  });
}

async function loadLibrary() {
  const [component] = await loadComponents();
  // @ts-ignore
  const library = window[component];
  if (!library.installed) {
    Vue.use(library.install);
    library.installed = true;
  }
  return library;
}

function load(name: string): Promise<VueConstructor> {
  // eslint-disable-next-line no-async-promise-executor
  return new Promise(async resolve => {
    const library = await loadLibrary();
    if (library[name]) {
      resolve(library[name]);
    } else {
      resolve(PremiumLoadingFailed);
    }
  });
}

export const PremiumStatistics = (): Promise<VueConstructor> => {
  return load('PremiumStatistics');
};

export const VaultEventsList = (): Promise<VueConstructor> => {
  return load('VaultEventsList');
};

export const LendingHistory = (): Promise<VueConstructor> => {
  return load('LendingHistory');
};

export const CompoundLendingDetails = (): Promise<VueConstructor> => {
  return load('CompoundLendingDetails');
};

export const CompoundBorrowingDetails = (): Promise<VueConstructor> => {
  return load('CompoundBorrowingDetails');
};

export const YearnVaultsProfitDetails = (): Promise<VueConstructor> => {
  return load('YearnVaultsProfitDetails');
};

export const AaveBorrowingDetails = (): Promise<VueConstructor> => {
  return load('AaveBorrowingDetails');
};

export const AaveEarnedDetails = (): Promise<VueConstructor> => {
  return load('AaveEarnedDetails');
};

export const Eth2Staking = (): Promise<VueConstructor> => {
  return load('Eth2Staking');
};

export const DexTradesTable = (): Promise<VueConstructor> => {
  return load('DexTradesTable');
};

export const UniswapDetails = (): Promise<VueConstructor> => {
  return load('UniswapDetails');
};

export const AdexStaking = (): Promise<VueConstructor> => {
  return load('AdexStaking');
};

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    rotki: {
      readonly useHostComponents: boolean;
      readonly version: number;
      readonly utils: ExposedUtilities;
      readonly debug?: DebugSettings;
    };
  }
}
