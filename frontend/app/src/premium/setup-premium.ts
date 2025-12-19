import * as VueUse from '@vueuse/core';
import * as VueUseShared from '@vueuse/shared';
import * as BigNumber from 'bignumber.js';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import {
  BrushComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components';
import * as EChartsCore from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import * as Vue from 'vue';
import VChart from 'vue-echarts';
import * as VueRouter from 'vue-router';
import * as zod from 'zod/v4';
import { app } from '@/main';

// Register only the needed echarts components for premium
EChartsCore.use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  TooltipComponent,
  GridComponent,
  DataZoomComponent,
  LegendComponent,
  BrushComponent,
  ToolboxComponent,
]);

export async function setupPremium(): Promise<void> {
  /**
   * If setup has run already no need to do it again
   */
  if (!window.Vue) {
    window.Vue = Vue;
    window.VueUse = VueUse;
    window.VueUseShared = VueUseShared;
    window.VueEcharts = VChart;
    window.ECharts = EChartsCore;
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
