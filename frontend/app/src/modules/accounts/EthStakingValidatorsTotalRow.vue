<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { useI18n } from 'vue-i18n';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import RowAppend from '@/modules/shell/components/RowAppend.vue';
import { useEthValidatorUtils } from '@/modules/staking/eth/use-eth-validator-utils';

const { columns, rows } = defineProps<{
  rows: Collection<EthereumValidator>;
  /** How many columns the table shows, so the totals line up under amount and value. */
  columns: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useTotal, useTotalAmount } = useEthValidatorUtils();
const totalValue = useTotal(() => rows);
const totalAmount = useTotalAmount(() => rows);
</script>

<template>
  <RowAppend
    label-colspan="4"
    :label="t('common.total')"
    :right-patch-colspan="columns - 2"
    variant="fixed"
  >
    <template #custom-columns>
      <td class="text-end">
        <AssetAmountDisplay
          asset="ETH"
          :amount="totalAmount"
        />
      </td>
    </template>
    <FiatDisplay :value="totalValue" />
  </RowAppend>
</template>
