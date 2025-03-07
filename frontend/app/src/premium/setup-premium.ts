import { app } from '@/main';
import * as VueUse from '@vueuse/core';
import * as VueUseShared from '@vueuse/shared';
import * as BigNumber from 'bignumber.js';
import * as Chart from 'chart.js';
import ChartJsPluginZoom from 'chartjs-plugin-zoom';
import * as Vue from 'vue';
import * as VueRouter from 'vue-router';
import * as zod from 'zod';

export async function setupPremium(): Promise<void> {
  /**
   * If setup has run already no need to do it again
   */
  if (!window.Vue) {
    window.Vue = Vue;
    window.VueUse = VueUse;
    window.VueUseShared = VueUseShared;
    window.Chart = Chart;
    window['chartjs-plugin-zoom'] = ChartJsPluginZoom;
    window.Chart = Chart;
    window.zod = zod;
    window.bn = BigNumber;
    window.VueRouter = VueRouter;
  }

  /**
   * Sometimes, window.Vue still exists, but the component registrations here are always gone during HMR.
   * So, they need to be registered again.
   */
  const { registerComponents } = await import('@/premium/register-components');
  registerComponents(app);
}
