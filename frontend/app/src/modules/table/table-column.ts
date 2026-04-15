import { z } from 'zod/v4';

export enum TableColumn {
  PERCENTAGE_OF_TOTAL_NET_VALUE = 'percentage_of_total_net_value',
  PERCENTAGE_OF_TOTAL_CURRENT_GROUP = 'percentage_of_total_current_group',
}

export const TableColumnEnum = z.array(z.enum(TableColumn));
