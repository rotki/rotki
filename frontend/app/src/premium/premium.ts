import Vue from 'vue';
import type * as Chart from 'chart.js';

class ComponentLoadFailedError extends Error {
  constructor() {
    super();
    this.name = 'ComponentLoadFailedError';
  }
}

const findComponents = (): string[] =>
  Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents')
  );

if (checkIfDevelopment()) {
  // @ts-ignore
  findComponents().forEach(component => (window[component] = undefined));
}

const loadComponents = async (): Promise<string[]> =>
  // eslint-disable-next-line no-async-promise-executor
  new Promise(async (resolve, reject) => {
    let components = findComponents();
    if (components.length > 0) {
      resolve(components);
      return;
    }

    const api = useStatisticsApi();
    const result = await api.queryStatisticsRenderer();
    const script = document.createElement('script');
    script.text = result;
    document.head.append(script);

    components = findComponents();

    if (components.length === 0) {
      reject(new Error('There was no component loaded'));
      return;
    }

    script.addEventListener('error', reject);
    resolve(components);
  });
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

  throw new ComponentLoadFailedError();
};

const PremiumLoading = async () =>
  import('@/components/premium/PremiumLoading.vue');
const PremiumLoadingError = async () =>
  import('@/components/premium/PremiumLoadingError.vue');
const ThemeSwitchLock = async () =>
  import('@/components/premium/ThemeSwitchLock.vue');

const createFactory = (
  component: Promise<any>,
  options?: { loading?: any; error?: any }
) => ({
  component,
  loading: options?.loading ?? PremiumLoading,
  error: options?.error ?? PremiumLoadingError,
  delay: 500,
  timeout: 30000
});

export const PremiumStatistics = () => createFactory(load('PremiumStatistics'));

export const VaultEventsList = () => createFactory(load('VaultEventsList'));

export const LendingHistory = () => createFactory(load('LendingHistory'));

export const CompoundLendingDetails = () =>
  createFactory(load('CompoundLendingDetails'));

export const CompoundBorrowingDetails = () =>
  createFactory(load('CompoundBorrowingDetails'));

export const YearnVaultsProfitDetails = () =>
  createFactory(load('YearnVaultsProfitDetails'));

export const AaveBorrowingDetails = () =>
  createFactory(load('AaveBorrowingDetails'));

export const AaveEarnedDetails = () => createFactory(load('AaveEarnedDetails'));

export const Eth2Staking = () => createFactory(load('Eth2Staking'));

export const UniswapDetails = () => createFactory(load('UniswapDetails'));

export const AssetAmountAndValueOverTime = () =>
  createFactory(load('AssetAmountAndValueOverTime'));

export const BalancerBalances = () => createFactory(load('BalancerBalances'));

export const ThemeChecker = () => createFactory(load('ThemeChecker'));

export const ThemeSwitch = () =>
  createFactory(load('ThemeSwitch'), {
    loading: ThemeSwitchLock,
    error: ThemeSwitchLock
  });

export const ThemeManager = () => createFactory(load('ThemeManager'));

export const Sushi = () => createFactory(load('Sushi'));

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    VueUse: any;
    VueUseShared: any;
    'chartjs-plugin-zoom': any;
    zod: any;
    bn: any;
  }
}
