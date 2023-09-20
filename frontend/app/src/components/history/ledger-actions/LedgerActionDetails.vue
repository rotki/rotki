<script setup lang="ts">
import { type PropType } from 'vue';
import { type LedgerActionEntry } from '@/types/history/ledger-action/ledger-actions';

const props = defineProps({
  span: {
    required: true,
    type: Number
  },
  item: {
    required: true,
    type: Object as PropType<LedgerActionEntry>
  }
});

const { item } = toRefs(props);
const { dark } = useTheme();
const { t } = useI18n();

const link = computed(() => get(item).link || '');
const { href, hasLink, onLinkClick } = useLinks(link);
</script>

<template>
  <TableExpandContainer visible :colspan="span">
    <template #title>
      {{ t('ledger_actions.details.title') }}
    </template>
    <VRow>
      <VCol cols="auto" class="font-medium">
        {{ t('ledger_actions.details.rate_asset') }}
      </VCol>
      <VCol>
        <AmountDisplay
          v-if="!!item.rate"
          :value="item.rate"
          :asset="item.rateAsset"
        />
        <span v-else>
          {{ t('ledger_actions.details.rate_data') }}
        </span>
      </VCol>
    </VRow>
    <VRow align="center">
      <VCol cols="auto" class="font-medium">
        {{ t('ledger_actions.details.link') }}
      </VCol>
      <VCol>
        <span v-if="!item.link">
          {{ t('ledger_actions.details.link_data') }}
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
            <span>{{ item.link }}</span>
          </VTooltip>
        </span>
      </VCol>
    </VRow>
    <NotesDisplay :notes="item.notes" />
  </TableExpandContainer>
</template>
