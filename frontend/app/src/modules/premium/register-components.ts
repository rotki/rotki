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
  RuiIcon,
  RuiMenu,
  RuiProgress,
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
import StatisticsGraphSettings from '@/modules/settings/StatisticsGraphSettings.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
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
  app.component('RuiChip', RuiChip);
  app.component('RuiDialog', RuiDialog);
  app.component('RuiMenu', RuiMenu);
  app.component('RuiColorPicker', RuiColorPicker);
  app.component('RuiProgress', RuiProgress);
  app.component('RuiDateTimePicker', RuiDateTimePicker);
}

/**
 * Registers the components the premium bundle renders by name.
 *
 * @remarks
 * Removing an entry breaks a bundle that asks for it, so treat this list as the host's contract
 * with components major 17. Per-entry version notes are not needed: a bundle refuses to render
 * below host version 30, so none can ask for anything older.
 */
export function registerComponents(app: App): void {
  app.component('HashLink', HashLink);
  app.component('PercentageDisplay', PercentageDisplay);
  app.component('DateDisplay', DateDisplay);
  app.component('AssetSelect', AssetSelect);
  app.component('StatisticsGraphSettings', StatisticsGraphSettings);
  app.component('ExportSnapshotDialog', ExportSnapshotDialog);
  app.component('HistoryEventsView', HistoryEventsView);
  app.component('MissingDailyPrices', MissingDailyPrices);
  app.component('NewGraphTooltipWrapper', NewGraphTooltipWrapper);
  app.component('FiatDisplay', FiatDisplay);
  app.component('ValueDisplay', ValueDisplay);

  ruiRegister(app);
  logger.info('Components registered');
}
