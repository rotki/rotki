import type { PremiumApi } from '@rotki/common';
import type { App, Component } from 'vue';
import { checkIfDevelopment } from '@shared/utils';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { app } from '@/main';
import { logger } from '@/utils/logging';

const PREMIUM_COMPONENTS_VERSION = 27;

type PremiumLibrary = {
  install: (app: App) => void;
  installed?: boolean;
  initPremiumApi?: (factory: () => PremiumApi, version: number) => void;
} & Record<string, Component>;

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

    // Dynamic import - setup-premium.ts and its heavy dependencies (ECharts, VueUse, etc.) go into separate chunk
    const { setupPremium } = await import('@/premium/setup-premium');
    await setupPremium();
    const api = useStatisticsApi();
    const result = await api.queryStatisticsRenderer();
    const script = document.createElement('script');
    script.text = result;
    document.head.append(script);

    components = findComponents();

    if (components.length === 0)
      throw new Error('There was no component loaded');

    return components;
  }
  finally {
    lock.disable();
  }
}

async function loadLibrary(): Promise<PremiumLibrary> {
  const [component] = await loadComponents();
  // @ts-expect-error component is dynamic and not added in the window type
  const library: PremiumLibrary = window[component];
  if (!library.installed) {
    app.use(library);
    library.installed = true;

    // Dynamic import - setup-interface.ts and its dependencies go into separate chunk
    const { createPremiumApi } = await import('@/premium/setup-interface');

    // Pass the factory and version to the library - factory will be called in component context
    if (library.initPremiumApi) {
      library.initPremiumApi(createPremiumApi, PREMIUM_COMPONENTS_VERSION);
    }
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
