import { VueConstructor } from 'vue';
import { service } from '@/services/rotkehlchen_service';
import Vue from 'vue';
import Chart from 'chart.js';
import moment from 'moment';

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.moment = moment;
};

export const PremiumStatistics = (): Promise<VueConstructor> => {
  return new Promise(async (resolve, reject) => {
    const result = await service.query_statistics_renderer();
    const script = document.createElement('script');
    script.text = result;
    document.head.appendChild(script);
    const components = Object.getOwnPropertyNames(window).filter(value =>
      value.startsWith('PremiumComponents')
    );
    if (components.length === 0) {
      reject(new Error('There was no component loaded'));
    }
    // @ts-ignore
    const library = window[components[0]];
    Vue.use(library.install);
    await library.prepare();
    resolve(library.PremiumStatistics);

    script.addEventListener('error', reject);
  });
};

declare global {
  interface Window {
    Vue: typeof Vue;
    Chart: typeof Chart;
    moment: typeof moment;
  }
}
