import * as CompositionAPI from '@vue/composition-api';
import { set } from '@vueuse/core';
import * as BigNumber from 'bignumber.js';
import * as Chart from 'chart.js';
import ChartJsPluginZoom from 'chartjs-plugin-zoom';
import { storeToRefs } from 'pinia';
import Vue from 'vue';
import * as zod from 'zod';
import { usePremiumStore } from '@/store/session/premium';

export const setupPremium = async () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window['chartjs-plugin-zoom'] = ChartJsPluginZoom;
  window.Chart = Chart;
  window['@vue/composition-api'] = CompositionAPI;
  window.zod = zod;
  window.bn = BigNumber;
  const { componentsLoaded } = storeToRefs(usePremiumStore());
  set(componentsLoaded, false);
  const { registerComponents } = await import('@/premium/register-components');
  registerComponents();
  set(componentsLoaded, true);
};
