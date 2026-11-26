<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import RowAppend from '@/modules/shell/components/RowAppend.vue';

defineProps<{
  /** The total of the rows still showing. */
  totalValue: BigNumber;
  /** Some row has details, so the table keeps a lead column the label has to skip. */
  anyExpansion: boolean;
  /** The kind of account group the table lists, which sets how many columns the label spans. */
  group?: 'evm' | 'xpub';
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RowAppend
    :label="t('common.total')"
    :left-patch-colspan="anyExpansion ? 1 : 0"
    :label-colspan="group && group === 'evm' ? 4 : 2"
    :is-mobile="false"
    variant="fixed"
  >
    <template #custom-columns>
      <td class="text-end">
        <FiatDisplay
          :value="totalValue"
          :loading="loading"
        />
      </td>
    </template>
  </RowAppend>
</template>
