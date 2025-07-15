import type { Component } from 'vue';
import { checkIfDevelopment } from '@shared/utils';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { app } from '@/main';
import { setupPremium } from '@/premium/setup-premium';
import { logger } from '@/utils/logging';

class AsyncLock {
  promise: Promise<void>;
  disable: () => void;

  private locked: boolean = false;

  get isLocked(): boolean {
    return this.locked;
  }

  constructor() {
    this.disable = (): void => {};
    this.promise = Promise.resolve();
  }

  enable(): void {
    this.locked = true;
    this.promise = new Promise(resolve => (this.disable = (): void => {
      this.locked = false;
      resolve();
    }));
  }
}

class ComponentLoadFailedError extends Error {
  constructor(component: string) {
    super(component);
    this.name = 'ComponentLoadFailedError';
  }
}

function findComponents(): string[] {
  return Object.getOwnPropertyNames(window).filter(value => value.startsWith('PremiumComponents'));
}

if (checkIfDevelopment()) {
  // @ts-expect-error component is dynamic and does not exist in the window type
  findComponents().forEach(component => (delete window[component]));
}

const lock = new AsyncLock();

async function loadComponents(): Promise<string[]> {
  try {
    if (lock.isLocked)
      await lock.promise;

    lock.enable();

    let components = findComponents();
    if (components.length > 0)
      return components;

    await setupPremium();
    const api = useStatisticsApi();
    const result = await api.queryStatisticsRenderer();
    const script = document.createElement('script');
    script.text = result;
    document.head.append(script);

    components = findComponents();

    if (components.length === 0)
      throw new Error('There was no component loaded');

    script.addEventListener('error', (e) => {
      console.error(e);
    });
    return components;
  }
  finally {
    lock.disable();
  }
}

export async function loadLibrary(): Promise<any> {
  const [component] = await loadComponents();
  // @ts-expect-error component is dynamic and not added in the window type
  const library = window[component];
  if (!library.installed) {
    app.use(library);
    library.installed = true;
  }
  return library;
}

async function load(name: string): Promise<Component> {
  try {
    const library = await loadLibrary();
    if (library[name])
      return library[name];
  }
  catch (error: any) {
    logger.error(error);
  }

  throw new ComponentLoadFailedError(name);
}

const PremiumLoading = defineAsyncComponent(async () => import('@/components/premium/PremiumLoading.vue'));
const PremiumLoadingError = defineAsyncComponent(async () => import('@/components/premium/PremiumLoadingError.vue'));

function createFactory(component: string, options?: { loading?: Component; error?: Component }): Component {
  return defineAsyncComponent({
    delay: 500,
    errorComponent: options?.error ?? PremiumLoadingError,
    loader: async () => load(component),
    loadingComponent: options?.loading ?? PremiumLoading,
    timeout: 30000,
  });
}

export const PremiumStatistics = createFactory('PremiumStatistics');

export const EthStaking = createFactory('EthStaking');

export const AssetAmountAndValueOverTime = createFactory('AssetAmountAndValueOverTime');

export const ThemeManager = createFactory('ThemeManager');

declare global {
  interface Window {
    Vue: any;
    VueEcharts: any;
    VueUse: any;
    VueUseShared: any;
    ECharts: any;
    zod: any;
    bn: any;
    VueRouter: any;
  }
}
