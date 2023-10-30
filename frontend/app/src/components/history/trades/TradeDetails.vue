<script setup lang="ts">
import { type TradeEntry } from '@/types/history/trade';

const props = withDefaults(
  defineProps<{
    span?: number;
    item: TradeEntry;
  }>(),
  {
    span: 1
  }
);

const { item } = toRefs(props);
const { dark } = useTheme();
const { t } = useI18n();

const link = computed(() => get(item).link || '');
const { href, hasLink, onLinkClick } = useLinks(link);
</script>

<template>
  <TableExpandContainer visible :colspan="span">
    <template #title>
      {{ t('closed_trades.details.title') }}
    </template>
    <VRow>
      <VCol cols="auto" class="font-medium">
        {{ t('closed_trades.details.fee') }}
      </VCol>
      <VCol>
        <AmountDisplay
          v-if="!!item.fee"
          class="closed-trades__trade__fee"
          :asset="item.feeCurrency"
          :value="item.fee"
        />
        <span v-else>-</span>
      </VCol>
    </VRow>
    <VRow align="center">
      <VCol cols="auto" class="font-medium">
        {{ t('closed_trades.details.link') }}
      </VCol>
      <VCol>
        <span v-if="!item.link">
          {{ t('closed_trades.details.link_data') }}
        </span>
        <span v-else>
          {{ item.link }}
          <VTooltip v-if="hasLink" top open-delay="600">
            <template #activator="{ on, attrs }">
              <VBtn
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
                <VIcon :small="true"> mdi-launch </VIcon>
              </VBtn>
            </template>
            {{ item.link }}
          </VTooltip>
        </span>
      </VCol>
    </VRow>
    <NotesDisplay :notes="item.notes" />
  </TableExpandContainer>
</template>
