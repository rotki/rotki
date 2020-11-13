import Chart from 'chart.js';
import moment from 'moment';
import Vue, { VueConstructor } from 'vue';
import Vuex from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetMovementDisplay from '@/components/display/AssetMovementDisplay.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import EventTypeDisplay from '@/components/display/EventTypeDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import PremiumLoadingFailed from '@/components/display/PremiumLoadingFailed.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import HashLink from '@/components/helper/HashLink.vue';
import { DebugSettings } from '@/electron-main/ipc';
import { api } from '@/services/rotkehlchen-api';

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.Vue.use(Vuex);
  window.moment = moment;
  window.rotki = {
    useHostComponents: true,
    version: 2
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

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    moment: typeof moment;
    rotki: {
      useHostComponents: boolean;
      version: number;
      debug?: DebugSettings;
    };
  }
}
