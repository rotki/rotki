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
    <v-row align="center">
      <v-col cols="auto" class="font-weight-medium">
        {{ $t('closed_trades.details.link') }}
      </v-col>
      <v-col>
        <span v-if="!item.link">
          {{ $t('closed_trades.details.link_data') }}
        </span>
        <span v-else>
          {{ item.link }}
          <v-tooltip v-if="hasLink(item)" top open-delay="600">
            <template #activator="{ on, attrs }">
              <v-btn
                small
                icon
                v-bind="attrs"
                color="primary"
                class="ml-2"
                :class="dark ? null : 'grey lighten-4'"
                :href="href(item.link)"
                :target="target"
                v-on="on"
                @click="openLink(item.link)"
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
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { interop } from '@/electron-interop';
import ThemeMixin from '@/mixins/theme-mixin';
import { TradeEntry } from '@/store/history/types';

export default defineComponent({
  name: 'TradeDetails',
  components: { NotesDisplay, TableExpandContainer },
  mixins: [ThemeMixin],
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
  },
  setup() {
    const hasLink = (trade: TradeEntry) => {
      return trade.link && trade.link.startsWith('http');
    };
    const openLink = (url: string) => {
      interop.openUrl(url);
    };

    const target = interop.isPackaged ? undefined : '_blank';

    const href = (url: string) => {
      if (interop.isPackaged) {
        return undefined;
      }
      return url;
    };

    return {
      hasLink,
      openLink,
      target,
      href
    };
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
