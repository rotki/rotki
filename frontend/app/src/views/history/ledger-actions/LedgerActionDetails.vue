<template>
  <table-expand-container visible :colspan="span">
    <template #title>
      {{ t('ledger_actions.details.title') }}
    </template>
    <v-row>
      <v-col cols="auto" class="font-weight-medium">
        {{ t('ledger_actions.details.rate_asset') }}
      </v-col>
      <v-col>
        <amount-display
          v-if="!!item.rate"
          :value="item.rate"
          :asset="item.rateAsset"
        />
        <span v-else>
          {{ t('ledger_actions.details.rate_data') }}
        </span>
      </v-col>
    </v-row>
    <v-row class="mt-2">
      <v-col cols="auto" class="font-weight-medium">
        {{ t('ledger_actions.details.link') }}
      </v-col>
      <v-col>
        {{ item.link ? item.link : t('ledger_actions.details.link_data') }}
      </v-col>
    </v-row>
    <notes-display :notes="item.notes" />
  </table-expand-container>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { LedgerActionEntry } from '@/store/history/types';

defineProps({
  span: {
    required: true,
    type: Number
  },
  item: {
    required: true,
    type: Object as PropType<LedgerActionEntry>
  }
});

const { t } = useI18n();
</script>
