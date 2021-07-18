import Chart from 'chart.js';
import Vue, { VueConstructor } from 'vue';
import PremiumLoadingFailed from '@/components/display/PremiumLoadingFailed.vue';
import { RotkiPremiumInterface } from '@/premium/types';
import { api } from '@/services/rotkehlchen-api';

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

export const AssetAmountAndValueOverTime = (): Promise<VueConstructor> => {
  return load('AssetAmountAndValueOverTime');
};

export const BalancerBalances = (): Promise<VueConstructor> => {
  return load('BalancerBalances');
};

export const ThemeSwitch = (): Promise<VueConstructor> => {
  return load('ThemeSwitch');
};

export const ThemeManager = (): Promise<VueConstructor> => {
  return load('ThemeManager');
};

export const Grants = (): Promise<VueConstructor> => {
  return load('Grants');
};

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    rotki: RotkiPremiumInterface;
  }
}
