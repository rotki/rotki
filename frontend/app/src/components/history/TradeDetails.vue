<template>
  <table-expand-container visible :colspan="span">
    <template #title>
      {{ $t('closed_trades.details.title') }}
    </template>
    <v-row>
      <v-col cols="auto" class="font-weight-medium">
        {{ $t('closed_trades.details.fee') }}
      </v-col>
      <v-col>
        <amount-display
          v-if="!!item.fee"
          class="closed-trades__trade__fee"
          :asset="item.feeCurrency"
          :value="item.fee"
        />
        <span v-else>-</span>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="auto" class="font-weight-medium">
        {{ $t('closed_trades.details.link') }}
      </v-col>
      <v-col>
        {{ item.link ? item.link : $t('closed_trades.details.link_data') }}
      </v-col>
    </v-row>
    <notes-display :notes="item.notes" />
  </table-expand-container>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { TradeEntry } from '@/store/history/types';

export default defineComponent({
  name: 'TradeDetails',
  components: { NotesDisplay, TableExpandContainer },
  props: {
    span: {
      type: Number,
      required: false,
      default: 1
    },
    item: {
      required: true,
      type: Object as PropType<TradeEntry>
    }
  }
});
</script>
<style scoped lang="scss">
::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
