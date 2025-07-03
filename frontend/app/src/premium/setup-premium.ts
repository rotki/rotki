import { app } from '@/main';
import * as VueUse from '@vueuse/core';
import * as VueUseShared from '@vueuse/shared';
import * as BigNumber from 'bignumber.js';
import * as ECharts from 'echarts';
import * as Vue from 'vue';
import VChart from 'vue-echarts';
import * as VueRouter from 'vue-router';
import * as zod from 'zod/v4';

export async function setupPremium(): Promise<void> {
  /**
   * If setup has run already no need to do it again
   */
  if (!window.Vue) {
    window.Vue = Vue;
    window.VueUse = VueUse;
    window.VueUseShared = VueUseShared;
    window.VueEcharts = VChart;
    window.ECharts = ECharts;
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
