import Vue from 'vue';
import type * as Chart from 'chart.js';

class ComponentLoadFailedError extends Error {
  constructor() {
    super();
    this.name = 'ComponentLoadFailedError';
  }
}

function findComponents(): string[] {
  return Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents'),
  );
}

if (checkIfDevelopment()) {
  // @ts-expect-error
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
}

export async function loadLibrary() {
  const [component] = await loadComponents();
  // @ts-expect-error
  const library = window[component];
  if (!library.installed) {
    Vue.use(library.install);
    library.installed = true;
  }
  return library;
}

async function load(name: string) {
  try {
    const library = await loadLibrary();
    if (library[name])
      return library[name];
  }
  catch (error: any) {
    logger.error(error);
  }

  throw new ComponentLoadFailedError();
}

async function PremiumLoading() {
  return import('@/components/premium/PremiumLoading.vue');
}

async function PremiumLoadingError() {
  return import('@/components/premium/PremiumLoadingError.vue');
}

async function ThemeSwitchLock() {
  return import('@/components/premium/ThemeSwitchLock.vue');
}

function createFactory(component: Promise<any>, options?: { loading?: any; error?: any }) {
  return {
    component,
    loading: options?.loading ?? PremiumLoading,
    error: options?.error ?? PremiumLoadingError,
    delay: 500,
    timeout: 30000,
  };
}

export const PremiumStatistics = () => createFactory(load('PremiumStatistics'));

export const VaultEventsList = () => createFactory(load('VaultEventsList'));

export const LendingHistory = () => createFactory(load('LendingHistory'));

export function CompoundLendingDetails() {
  return createFactory(load('CompoundLendingDetails'));
}

export function CompoundBorrowingDetails() {
  return createFactory(load('CompoundBorrowingDetails'));
}

export function YearnVaultsProfitDetails() {
  return createFactory(load('YearnVaultsProfitDetails'));
}

export function AaveBorrowingDetails() {
  return createFactory(load('AaveBorrowingDetails'));
}

export const AaveEarnedDetails = () => createFactory(load('AaveEarnedDetails'));

export const EthStaking = () => createFactory(load('EthStaking'));

export const UniswapDetails = () => createFactory(load('UniswapDetails'));

export function AssetAmountAndValueOverTime() {
  return createFactory(load('AssetAmountAndValueOverTime'));
}

export const BalancerBalances = () => createFactory(load('BalancerBalances'));

export const ThemeChecker = () => createFactory(load('ThemeChecker'));

export function ThemeSwitch() {
  return createFactory(load('ThemeSwitch'), {
    loading: ThemeSwitchLock,
    error: ThemeSwitchLock,
  });
}

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
