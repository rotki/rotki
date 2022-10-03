import * as Chart from 'chart.js';
import Vue from 'vue';
import PremiumLoading from '@/components/premium/PremiumLoading.vue';
import PremiumLoadingError from '@/components/premium/PremiumLoadingError.vue';
import ThemeSwitchLock from '@/components/premium/ThemeSwitchLock.vue';
import { useStatisticsApi } from '@/services/statistics/statistics-api';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';

class ComponentLoadFailed extends Error {}

const findComponents = (): string[] =>
  Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents')
  );

if (checkIfDevelopment()) {
  // @ts-ignore
  findComponents().forEach(component => (window[component] = undefined));
}

const loadComponents = async (): Promise<string[]> => {
  // eslint-disable-next-line no-async-promise-executor
  return new Promise(async (resolve, reject) => {
    let components = findComponents();
    if (components.length > 0) {
      resolve(components);
      return;
    }

    const api = useStatisticsApi();
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
};

export const loadLibrary = async () => {
  const [component] = await loadComponents();
  // @ts-ignore
  const library = window[component];
  if (!library.installed) {
    Vue.use(library.install);
    library.installed = true;
  }
  return library;
};

const load = async (name: string) => {
  try {
    const library = await loadLibrary();
    if (library[name]) {
      return library[name];
    }
  } catch (e: any) {
    logger.error(e);
  }

  throw new ComponentLoadFailed();
};

const createFactory = (
  component: Promise<any>,
  options?: { loading?: any; error?: any }
) => ({
  component: component,
  loading: options?.loading ?? PremiumLoading,
  error: options?.error ?? PremiumLoadingError,
  delay: 500,
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
    VueUse: any;
    'chartjs-plugin-zoom': any;
    zod: any;
    bn: any;
  }
}
