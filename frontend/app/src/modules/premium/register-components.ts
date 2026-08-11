import type { App } from 'vue';
import {
  RuiAlert,
  RuiButton,
  RuiButtonGroup,
  RuiCard,
  RuiChip,
  RuiColorPicker,
  RuiDataTable,
  RuiDateTimePicker,
  RuiDialog,
  RuiDivider,
  RuiIcon,
  RuiMenu,
  RuiProgress,
  RuiSlider,
  RuiTextField,
  RuiTooltip,
} from '@rotki/ui-library';
import {
  FiatDisplay,
  ValueDisplay,
} from '@/modules/assets/amount-display/components';
import { logger } from '@/modules/core/common/logging/logging';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import AssetBalanceStatisticSourceSetting from '@/modules/settings/AssetBalanceStatisticSourceSetting.vue';
import StatisticsGraphSettings from '@/modules/settings/StatisticsGraphSettings.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import MissingDailyPrices from '@/modules/statistics/MissingDailyPrices.vue';
import NewGraphTooltipWrapper from '@/modules/statistics/NewGraphTooltipWrapper.vue';

function ruiRegister(app: App): void {
  app.component('RuiAlert', RuiAlert);
  app.component('RuiIcon', RuiIcon);
  app.component('RuiButton', RuiButton);
  app.component('RuiTooltip', RuiTooltip);
  app.component('RuiTextField', RuiTextField);
  app.component('RuiButtonGroup', RuiButtonGroup);
  app.component('RuiCard', RuiCard);
  app.component('RuiDataTable', RuiDataTable);
  app.component('RuiDivider', RuiDivider);
  app.component('RuiChip', RuiChip);
  app.component('RuiMenu', RuiMenu);
  app.component('RuiSlider', RuiSlider);
  app.component('RuiDialog', RuiDialog);
  app.component('RuiColorPicker', RuiColorPicker);
  app.component('RuiProgress', RuiProgress);
  app.component('RuiDateTimePicker', RuiDateTimePicker);
}

/**
 * Components registered here are also handed to the premium bundle, which renders them by name.
 *
 * Every entry below is used by components major 16. The per-component "first available in version
 * N" trail this list used to carry went back to version 1 (rotki 1.19) and is gone: a bundle now
 * refuses to render below host version 29, so no supported bundle can ask for anything older, and
 * git history holds the record for anyone who needs it.
 */
export function registerComponents(app: App): void {
  app.component('HashLink', HashLink);
  app.component('BalanceDisplay', BalanceDisplay);
  app.component('PercentageDisplay', PercentageDisplay);
  app.component('DateDisplay', DateDisplay);
  app.component('AssetSelect', AssetSelect);
  app.component('StatisticsGraphSettings', StatisticsGraphSettings);
  app.component('ExportSnapshotDialog', ExportSnapshotDialog);
  app.component('MenuTooltipButton', MenuTooltipButton);
  app.component('HistoryEventsView', HistoryEventsView);
  app.component('AssetBalanceStatisticSourceSetting', AssetBalanceStatisticSourceSetting);
  app.component('MissingDailyPrices', MissingDailyPrices);
  app.component('NewGraphTooltipWrapper', NewGraphTooltipWrapper);
  app.component('FiatDisplay', FiatDisplay);
  app.component('ValueDisplay', ValueDisplay);

  ruiRegister(app);
  logger.info('Components registered');
}
