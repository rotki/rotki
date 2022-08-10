import * as CompositionAPI from '@vue/composition-api';
import * as BigNumber from 'bignumber.js';
import * as Chart from 'chart.js';
import ChartJsPluginZoom from 'chartjs-plugin-zoom';
import Vue from 'vue';
import * as zod from 'zod';
import { registerComponents } from '@/premium/register-components';

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window['chartjs-plugin-zoom'] = ChartJsPluginZoom;
  window.Chart = Chart;
  window['@vue/composition-api'] = CompositionAPI;
  window.zod = zod;
  window.bn = BigNumber;
  registerComponents();
};
