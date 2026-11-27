<script setup lang="ts">
import type { AssetUpdateConflictResult, ConflictResolution } from '@/modules/assets/types';
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import { RuiAlert, RuiButton, RuiCard, RuiRadio, RuiRadioGroup } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import StageLayout from '@/modules/auth/stage/StageLayout.vue';
import AssetConflictReviewRow from '@/modules/auth/unlock-flow/AssetConflictReviewRow.vue';
import { useAssetConflictResolution } from '@/modules/shell/app/use-asset-conflict-resolution';

const { conflicts, version } = defineProps<{
  conflicts: AssetUpdateConflictResult[];
  /** The asset database version the update stops at. */
  version: number;
}>();

const emit = defineEmits<{
  resolve: [resolution: ConflictResolution];
  skip: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Settle every asset one way, or pick per asset. */
type Choice = ConflictResolutionStrategy | 'manual';

const choice = ref<Choice>('remote');

const {
  duplicateIdentifiers,
  enableManualResolution,
  modelResolution,
  onStrategyChange,
  setResolution,
  valid,
  warnDuplicate,
} = useAssetConflictResolution(() => conflicts);

const manual = computed<boolean>(() => get(choice) === 'manual');

const choices = computed<{ value: Choice; label: string; hint: string }[]>(() => [
  { hint: t('unlock_flow.asset_update.conflicts.choice.remote_hint'), label: t('unlock_flow.asset_update.conflicts.choice.remote'), value: 'remote' },
  { hint: t('unlock_flow.asset_update.conflicts.choice.local_hint'), label: t('unlock_flow.asset_update.conflicts.choice.local'), value: 'local' },
  { hint: t('unlock_flow.asset_update.conflicts.choice.manual_hint'), label: t('unlock_flow.asset_update.conflicts.choice.manual'), value: 'manual' },
]);

watch(choice, (current) => {
  if (current === 'manual')
    enableManualResolution();
  else
    setResolution(current);
});

/** How many assets are set to keep the local edit, which the review header reports. */
const keptLocal = computed<number>(() => Object.values(get(modelResolution)).filter(strategy => strategy === 'local').length);

function choose(identifier: string, strategy: ConflictResolutionStrategy): void {
  modelResolution.value[identifier] = strategy;
  onStrategyChange(strategy);
}

// Starts on the default choice right away, so Apply is ready on the first render.
setResolution('remote');
</script>

<template>
  <StageLayout
    :wide="manual"
    data-testid="asset-conflicts"
  >
    <template #title>
      {{ t('unlock_flow.asset_update.conflicts.title') }}
    </template>
    <template #subtitle>
      {{ t('unlock_flow.asset_update.conflicts.subtitle', { count: conflicts.length, version }, conflicts.length) }}
    </template>

    <RuiAlert
      v-if="warnDuplicate"
      type="warning"
      data-testid="asset-conflicts-duplicate"
    >
      <i18n-t
        scope="global"
        keypath="conflict_dialog.duplicate_warn"
        tag="span"
      >
        <template #identifiers>
          <strong>{{ duplicateIdentifiers.join(', ') }}</strong>
        </template>
      </i18n-t>
    </RuiAlert>

    <RuiCard variant="outlined">
      <RuiRadioGroup
        v-model="choice"
        color="primary"
        details="hidden"
        class="flex flex-col gap-2"
        data-testid="asset-conflicts-choice"
      >
        <RuiRadio
          v-for="option in choices"
          :key="option.value"
          :value="option.value"
          details="hidden"
        >
          <span class="flex flex-col">
            <span class="text-body-2 font-medium">{{ option.label }}</span>
            <span class="text-caption text-rui-text-secondary">{{ option.hint }}</span>
          </span>
        </RuiRadio>
      </RuiRadioGroup>
    </RuiCard>

    <RuiCard
      v-if="manual"
      variant="outlined"
      no-padding
      class="overflow-hidden"
    >
      <div
        class="px-4 py-3 border-b border-default text-body-2 text-rui-text-secondary"
        aria-live="polite"
        data-testid="asset-conflicts-summary"
      >
        {{ t('unlock_flow.asset_update.conflicts.review.summary', { local: keptLocal, remote: conflicts.length - keptLocal }) }}
      </div>
      <ul
        class="divide-y divide-default max-h-[50vh] overflow-y-auto"
        data-testid="asset-conflicts-list"
      >
        <AssetConflictReviewRow
          v-for="conflict in conflicts"
          :key="conflict.identifier"
          :conflict="conflict"
          :strategy="modelResolution[conflict.identifier]"
          @choose="choose(conflict.identifier, $event)"
        />
      </ul>
    </RuiCard>

    <template #actions>
      <RuiButton
        color="primary"
        :disabled="!valid"
        data-testid="asset-conflicts-apply"
        @click="emit('resolve', modelResolution)"
      >
        {{ t('unlock_flow.asset_update.conflicts.actions.apply') }}
      </RuiButton>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="asset-conflicts-skip"
        @click="emit('skip')"
      >
        {{ t('unlock_flow.asset_update.conflicts.actions.skip') }}
      </RuiButton>
    </template>
  </StageLayout>
</template>
