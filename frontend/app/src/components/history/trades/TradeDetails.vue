<script setup lang="ts">
import type { TradeEntry } from '@/types/history/trade';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useLinks } from '@/composables/links';

const props = defineProps<{ item: TradeEntry }>();

const { item } = toRefs(props);
const { t } = useI18n();

const link = computed(() => get(item).link || '');
const { hasLink, href, onLinkClick } = useLinks(link);
</script>

<template>
  <div>
    <h6 class="text-h6 mb-4">
      {{ t('closed_trades.details.title') }}
    </h6>
    <RuiCard content-class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3">
      <span class="font-medium">
        {{ t('common.fee') }}
      </span>

      <AmountDisplay
        v-if="!!item.fee && item.feeCurrency"
        class="closed-trades__trade__fee"
        :asset="item.feeCurrency"
        :value="item.fee"
      />
      <template v-else>
        -
      </template>

      <span class="font-medium">
        {{ t('closed_trades.details.link') }}
      </span>

      <div
        v-if="item.link"
        class="flex items-center gap-3"
      >
        {{ item.link }}
        <RuiTooltip
          v-if="hasLink"
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              tag="a"
              icon
              variant="text"
              class="!bg-rui-grey-200 dark:!bg-rui-grey-900 hover:!bg-rui-grey-100 hover:dark:!bg-rui-grey-800"
              size="sm"
              color="primary"
              :href="href"
              target="_blank"
              @click="onLinkClick()"
            >
              <RuiIcon
                name="lu-external-link"
                size="12"
              />
            </RuiButton>
          </template>
          {{ item.link }}
        </RuiTooltip>
      </div>

      <template v-else>
        -
      </template>

      <template v-if="item.notes">
        <span class="font-medium">
          {{ t('common.notes') }}
        </span>
        <div class="break-words max-w-[70vw]">
          {{ item.notes }}
        </div>
      </template>
    </RuiCard>
  </div>
</template>
