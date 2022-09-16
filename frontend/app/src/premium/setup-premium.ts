import * as VueUse from '@vueuse/core';
import * as BigNumber from 'bignumber.js';
import * as Chart from 'chart.js';
import ChartJsPluginZoom from 'chartjs-plugin-zoom';
import * as Vue from 'vue';
import { Ref } from 'vue';
import * as zod from 'zod';

export const setupPremium = async (componentsLoaded: Ref<boolean>) => {
  window.Vue = Vue;
  window.VueUse = VueUse;
  window.Chart = Chart;
  window['chartjs-plugin-zoom'] = ChartJsPluginZoom;
  window.Chart = Chart;
  window.zod = zod;
  window.bn = BigNumber;
  set(componentsLoaded, false);
  const { registerComponents } = await import('@/premium/register-components');
  registerComponents();
  set(componentsLoaded, true);
};
