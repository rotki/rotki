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
                :target="target"
                v-on="on"
                @click="openLink()"
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
import { get } from '@vueuse/core';
import { computed, PropType, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { useTheme } from '@/composables/common';
import { useInterop } from '@/electron-interop';
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
const { isPackaged, openUrl } = useInterop();

const hasLink = computed(() => {
  const { link } = get(item);
  return link && link.startsWith('http');
});

const target = isPackaged ? undefined : '_blank';

const href = computed(() => {
  if (isPackaged) {
    return undefined;
  }
  const { link } = get(item);
  return link ?? '';
});

const openLink = () => {
  const { link } = get(item);
  if (link) {
    openUrl(link);
  }
};
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
