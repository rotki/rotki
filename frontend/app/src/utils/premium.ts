import Chart from 'chart.js';
import moment from 'moment';
import Vue, { VueConstructor } from 'vue';
import Vuex from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumLoadingFailed from '@/components/display/PremiumLoadingFailed.vue';
import { api } from '@/services/rotkehlchen-api';

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.Vue.use(Vuex);
  window.moment = moment;
  window.rotki = {
    useHostComponents: true
  };
  // Globally registered components are also provided to the premium components.
  Vue.component('AmountDisplay', AmountDisplay);
};

function findComponents(): string[] {
  return Object.getOwnPropertyNames(window).filter(value =>
    value.startsWith('PremiumComponents')
  );
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

export const DsrMovementHistory = (): Promise<VueConstructor> => {
  return load('DsrMovementHistory');
};

export const VaultEventsList = (): Promise<VueConstructor> => {
  return load('VaultEventsList');
};

export const LendingHistory = (): Promise<VueConstructor> => {
  return load('LendingHistory');
};

declare global {
  interface Window {
    Vue: any;
    Chart: typeof Chart;
    moment: typeof moment;
    rotki: {
      useHostComponents: boolean;
    };
  }
}
