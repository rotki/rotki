/* eslint-disable @rotki/max-dependencies */
import type { App } from 'vue';
import {
  RuiAccordion,
  RuiAccordions,
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
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import {
  AssetAmountDisplay,
  AssetValueDisplay,
  FiatDisplay,
  ValueDisplay,
} from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import AssetLink from '@/modules/assets/AssetLink.vue';
import { logger } from '@/modules/core/common/logging/logging';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import ExportSnapshotDialog from '@/modules/dashboard/ExportSnapshotDialog.vue';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import RangeSelector from '@/modules/reports/RangeSelector.vue';
import AssetBalanceStatisticSourceSetting from '@/modules/settings/AssetBalanceStatisticSourceSetting.vue';
import StatisticsGraphSettings from '@/modules/settings/StatisticsGraphSettings.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import PaginatedCards from '@/modules/shell/components/PaginatedCards.vue';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
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
  app.component('RuiAccordions', RuiAccordions);
  app.component('RuiAccordion', RuiAccordion);
  app.component('RuiDateTimePicker', RuiDateTimePicker);
}

export function registerComponents(app: App): void {
  // Globally registered components are also provided to the premium components.
  // AmountDisplay was removed at 1.42;
  // version: 1
  app.component('HashLink', HashLink);
  app.component('AssetDetails', AssetDetails);
  // DefiProtocolIcon was removed in 1.37;
  // version: 2
  //  CryptoIcon was replaced with AssetIcon on v11
  app.component('BalanceDisplay', BalanceDisplay);
  // version: 3
  app.component('PercentageDisplay', PercentageDisplay);
  // version: 4
  app.component('BlockchainAccountSelector', BlockchainAccountSelector);
  app.component('DateDisplay', DateDisplay);
  app.component('LocationDisplay', LocationDisplay);
  // version 5
  app.component('AssetSelect', AssetSelect);
  // version 6
  app.component('DateTimePicker', DateTimePicker);
  // version 8
  app.component('CardTitle', CardTitle);
  // version 9
  // LiquidityPoolSelector removed at 1.37
  app.component('TableFilter', TableFilter);
  // version 11
  app.component('AssetIcon', AssetIcon);
  // version 12 - 1.19
  app.component('RangeSelector', RangeSelector);
  app.component('ConfirmDialog', ConfirmDialog);
  // Version 13 - 1.20
  // UniswapPoolDetails was removed at 1.37
  // Version 14 - 1.21
  app.component('PaginatedCards', PaginatedCards);
  app.component('AssetLink', AssetLink);
  // Version 15 - 1.21.2
  app.component('StatisticsGraphSettings', StatisticsGraphSettings);
  // Version 16 - 1.23
  app.component('AmountInput', AmountInput);
  // Version 17 - 1.24
  app.component('ExportSnapshotDialog', ExportSnapshotDialog);
  // Version 18 - 1.25
  app.component('MenuTooltipButton', MenuTooltipButton);
  // 'GraphTooltipWrapper' removed at 1.40
  // Version 19 - 1.26
  // LpPoolIcon was removed at 1.37
  // Version 20 - 1.27
  app.component('BadgeDisplay', BadgeDisplay);
  // Version 21 - 1.28
  app.component('HistoryEventsView', HistoryEventsView);
  // Version 24 - 1.31
  // LpPoolHeader was removed at 1.37
  app.component('RowAppend', RowAppend);
  // Version 25 - 1.32
  // UniswapPoolAssetBalance was removed at 1.37
  // Version 26 - 1.34
  app.component('RefreshButton', RefreshButton);
  app.component('AssetBalanceStatisticSourceSetting', AssetBalanceStatisticSourceSetting);

  app.component('MissingDailyPrices', MissingDailyPrices);

  app.component('NewGraphTooltipWrapper', NewGraphTooltipWrapper);

  // Version 27 - Amount display components
  app.component('FiatDisplay', FiatDisplay);
  app.component('AssetValueDisplay', AssetValueDisplay);
  app.component('AssetAmountDisplay', AssetAmountDisplay);
  app.component('ValueDisplay', ValueDisplay);

  ruiRegister(app);
  logger.info('Components registered');
}
