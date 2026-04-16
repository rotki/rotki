import { LineChart, PieChart } from 'echarts/charts';
import {
  BrushComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

export function initGraph(): void {
  use([
    CanvasRenderer,
    LineChart,
    TooltipComponent,
    GridComponent,
    DataZoomComponent,
    PieChart,
    LegendComponent,
    BrushComponent,
    ToolboxComponent,
  ]);
}
