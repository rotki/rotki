<template>
  <table-expand-container visible :colspan="span">
    <template #title>
      {{ tc('closed_trades.details.title') }}
    </template>
    <v-row>
      <v-col cols="auto" class="font-weight-medium">
        {{ tc('closed_trades.details.fee') }}
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
    <v-row align="center">
      <v-col cols="auto" class="font-weight-medium">
        {{ tc('closed_trades.details.link') }}
      </v-col>
      <v-col>
        <span v-if="!item.link">
          {{ tc('closed_trades.details.link_data') }}
        </span>
        <span v-else>
          {{ item.link }}
          <v-tooltip v-if="hasLink" top open-delay="600">
            <template #activator="{ on, attrs }">
              <v-btn
                small
                icon
                v-bind="attrs"
                color="primary"
                class="ml-2"
                :class="dark ? null : 'grey lighten-4'"
                :href="href"
                target="_blank"
                v-on="on"
                @click="onLinkClick()"
              >
                <v-icon :small="true"> mdi-launch </v-icon>
              </v-btn>
            </template>
            <span>{{ item.link }}</span>
          </v-tooltip>
        </span>
      </v-col>
    </v-row>
    <notes-display :notes="item.notes" />
  </table-expand-container>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { useTheme } from '@/composables/common';
import { useLinks } from '@/composables/links';
import { TradeEntry } from '@/store/history/types';

const props = defineProps({
  span: {
    type: Number,
    required: false,
    default: 1
  },
  item: {
    required: true,
    type: Object as PropType<TradeEntry>
  }
});

const { item } = toRefs(props);
const { dark } = useTheme();
const { tc } = useI18n();

const link = computed(() => get(item).link || '');
const { href, hasLink, onLinkClick } = useLinks(link);
</script>
<style scoped lang="scss">
:deep() {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
