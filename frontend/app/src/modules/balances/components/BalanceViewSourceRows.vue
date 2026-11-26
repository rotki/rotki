<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { type SourceDifference, useSourceDifferences } from '@/modules/dashboard/holdings/use-history-holdings-contributions';
import { useSourceKindLabel } from '@/modules/dashboard/holdings/use-source-kind-label';

/** A section heading in the panel's figures grid; matches the panel's own headings. */
const HEADING = 'col-span-3 mb-1 text-xs font-medium tracking-wide text-rui-text-secondary';

/** The third column's notes: one step quieter than labels, so the amounts lead. */
const NOTE = 'truncate text-xs text-rui-text-disabled';

const { t } = useI18n({ useScope: 'global' });

const sources = useSourceDifferences();
const kindLabel = useSourceKindLabel();

function basisLabel({ basis }: SourceDifference): string {
  if (basis === 'derived')
    return t('balance_view.basis_derived');
  return basis === 'queried' ? t('balance_view.basis_live') : t('balance_view.not_in_history');
}
</script>

<template>
  <template v-if="sources.length > 0">
    <h4
      class="mt-3"
      :class="HEADING"
      data-testid="balance-view-panel-sources"
    >
      {{ t('balance_view.by_source') }}
    </h4>
    <template
      v-for="source in sources"
      :key="source.kind"
    >
      <span class="truncate">{{ kindLabel(source.kind) }}</span>
      <FiatDisplay
        class="justify-self-end"
        :class="{ 'text-rui-warning': source.basis === 'derived' && !source.delta.isZero() }"
        :value="source.delta"
      />
      <span
        :class="NOTE"
        :data-basis="source.basis"
      >
        {{ basisLabel(source) }}
      </span>
    </template>
  </template>
</template>
