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
  // RuiAccordion(s) removed at 1.44
}

export function registerComponents(app: App): void {
  // Globally registered components are also provided to the premium components.
  // AmountDisplay was removed at 1.42;
  // version: 1
  app.component('HashLink', HashLink);
  // AssetDetails removed at 1.44
  // DefiProtocolIcon was removed in 1.37;
  // version: 2
  //  CryptoIcon was replaced with AssetIcon on v11
  app.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  app.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  // BlockchainAccountSelector removed at 1.44
  app.component('DateDisplay', DateDisplay);
  // LocationDisplay removed at 1.44
  // version 5
  app.component('AssetSelect', AssetSelect);
  // version 6
  // DateTimePicker removed at 1.44
  // version 8
  // CardTitle removed at 1.44
  // version 9
  // LiquidityPoolSelector removed at 1.37
  // TableFilter removed at 1.44
  // version 11
  // AssetIcon removed at 1.44
  // version 12 - 1.19
  // RangeSelector and ConfirmDialog removed at 1.44
  // Version 13 - 1.20
  // UniswapPoolDetails was removed at 1.37
  // Version 14 - 1.21
  // PaginatedCards and AssetLink removed at 1.44
  // Version 15 - 1.21.2
  app.component('StatisticsGraphSettings', StatisticsGraphSettings);
  // Version 16 - 1.23
  // AmountInput removed at 1.44
  // Version 17 - 1.24
  app.component('ExportSnapshotDialog', ExportSnapshotDialog);
  // Version 18 - 1.25
  app.component('MenuTooltipButton', MenuTooltipButton);
  // 'GraphTooltipWrapper' removed at 1.40
  // Version 19 - 1.26
  // LpPoolIcon was removed at 1.37
  // Version 20 - 1.27
  // BadgeDisplay removed at 1.44
  // Version 21 - 1.28
  app.component('HistoryEventsView', HistoryEventsView);
  // Version 24 - 1.31
  // LpPoolHeader was removed at 1.37
  // RowAppend removed at 1.44
  // Version 25 - 1.32
  // UniswapPoolAssetBalance was removed at 1.37
  // Version 26 - 1.34
  // RefreshButton removed at 1.44
  app.component('AssetBalanceStatisticSourceSetting', AssetBalanceStatisticSourceSetting);

  app.component('MissingDailyPrices', MissingDailyPrices);

  app.component('NewGraphTooltipWrapper', NewGraphTooltipWrapper);

  // Version 27 - Amount display components
  app.component('FiatDisplay', FiatDisplay);
  // AssetValueDisplay and AssetAmountDisplay removed at 1.44
  app.component('ValueDisplay', ValueDisplay);

  ruiRegister(app);
  logger.info('Components registered');
}
