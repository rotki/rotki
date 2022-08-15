import * as Chart from 'chart.js';
import Vue, { VueConstructor } from 'vue';
import PremiumLoading from '@/components/premium/PremiumLoading.vue';
import PremiumLoadingError from '@/components/premium/PremiumLoadingError.vue';
import ThemeSwitchLock from '@/components/premium/ThemeSwitchLock.vue';
import { api } from '@/services/rotkehlchen-api';
import { checkIfDevelopment } from '@/utils/env-utils';

function findComponents(): string[] {
  return Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents')
  );
}

if (checkIfDevelopment()) {
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
      resolve(PremiumLoadingError as VueConstructor);
    }
  });
}

const createFactory = (
  component: Promise<VueConstructor>,
  options?: { loading?: VueConstructor; error?: VueConstructor }
) => ({
  component: component,
  loading: options?.loading ?? PremiumLoading,
  error: options?.error ?? PremiumLoadingError,
  delay: 100,
  timeout: 30000
});

export const PremiumStatistics = () => {
  return createFactory(load('PremiumStatistics'));
};

export const VaultEventsList = () => {
  return createFactory(load('VaultEventsList'));
};

export const LendingHistory = () => {
  return createFactory(load('LendingHistory'));
};

export const CompoundLendingDetails = () => {
  return createFactory(load('CompoundLendingDetails'));
};

export const CompoundBorrowingDetails = () => {
  return createFactory(load('CompoundBorrowingDetails'));
};

export const YearnVaultsProfitDetails = () => {
  return createFactory(load('YearnVaultsProfitDetails'));
};

export const AaveBorrowingDetails = () => {
  return createFactory(load('AaveBorrowingDetails'));
};

export const AaveEarnedDetails = () => {
  return createFactory(load('AaveEarnedDetails'));
};

export const Eth2Staking = () => {
  return createFactory(load('Eth2Staking'));
};

export const DexTradesTable = () => {
  return createFactory(load('DexTradesTable'));
};

export const UniswapDetails = () => {
  return createFactory(load('UniswapDetails'));
};

export const AdexStaking = () => {
  return createFactory(load('AdexStaking'));
};

export const AssetAmountAndValueOverTime = () => {
  return createFactory(load('AssetAmountAndValueOverTime'));
};

export const BalancerBalances = () => {
  return createFactory(load('BalancerBalances'));
};

export const ThemeChecker = () => {
  return createFactory(load('ThemeChecker'));
};

export const ThemeSwitch = () => {
  return createFactory(load('ThemeSwitch'), {
    loading: ThemeSwitchLock,
    error: ThemeSwitchLock
  });
};

export const ThemeManager = () => {
  return createFactory(load('ThemeManager'));
};

export const Grants = () => {
  return createFactory(load('Grants'));
};

export const Sushi = () => {
  return createFactory(load('Sushi'));
};

export const LiquityTroveEvents = () => {
  return createFactory(load('LiquityTroveEvents'));
};

export const LiquityStakeEvents = () => {
  return createFactory(load('LiquityStakeEvents'));
};

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    '@vue/composition-api': any;
    'chartjs-plugin-zoom': any;
    zod: any;
    bn: any;
  }
}
