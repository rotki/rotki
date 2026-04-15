import type { RuiIcons } from '@rotki/ui-library';

export interface TradeLocationData {
  readonly identifier: string;
  readonly name: string;
  readonly icon?: RuiIcons | null;
  readonly image?: string | null;
  readonly detailPath?: string | null;
}
