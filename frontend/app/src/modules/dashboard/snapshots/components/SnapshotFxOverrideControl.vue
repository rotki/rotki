<script setup lang="ts">
import { bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useSnapshotFxOverride } from '@/modules/dashboard/snapshots/composables/use-snapshot-fx-override';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const { timestamp } = defineProps<{
  timestamp: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  clearOverride,
  currencySymbol,
  currentOverride,
  isUsd,
  loading,
  rate,
  rateReady,
  refreshOverride,
  saving,
  setOverride,
} = useSnapshotFxOverride(() => timestamp);

const open = ref<boolean>(false);
const input = ref<string>('');

const hasOverride = computed<boolean>(() => isDefined(currentOverride));

function startEdit(): void {
  set(input, get(rateReady) ? get(rate).toFixed() : '');
  set(open, true);
}

async function apply(): Promise<void> {
  const value = bigNumberify(get(input));
  if (!value.isPositive())
    return;
  const success = await setOverride(value);
  if (success)
    set(open, false);
}

async function clear(): Promise<void> {
  const success = await clearOverride();
  if (success)
    set(open, false);
}

watch(() => timestamp, () => {
  set(open, false);
  startPromise(refreshOverride());
});

onMounted(() => {
  startPromise(refreshOverride());
});
</script>

<template>
  <div
    v-if="!isUsd"
    data-testid="snapshot-fx-override"
  >
    <div
      v-if="loading"
      class="flex items-center gap-2 text-body-2 text-rui-text-secondary"
    >
      <RuiProgress
        circular
        thickness="2"
        variant="indeterminate"
        color="primary"
        size="14"
      />
      {{ t('dashboard.snapshot.detail.fx_override.loading', { symbol: currencySymbol }) }}
    </div>

    <RuiAlert
      v-else-if="!rateReady"
      type="warning"
    >
      <template #title>
        {{ t('dashboard.snapshot.detail.fx_override.missing.title') }}
      </template>
      <p class="text-body-2 mb-2">
        {{ t('dashboard.snapshot.detail.fx_override.missing.description', { symbol: currencySymbol }) }}
      </p>
      <RuiButton
        v-if="!open"
        size="sm"
        color="warning"
        data-testid="snapshot-fx-override-set"
        @click="startEdit()"
      >
        {{ t('dashboard.snapshot.detail.fx_override.set_rate') }}
      </RuiButton>
    </RuiAlert>

    <div
      v-else
      class="flex flex-wrap items-center gap-2 text-body-2"
    >
      <span class="text-rui-text-secondary">
        {{ t('dashboard.snapshot.detail.fx_override.label', { symbol: currencySymbol }) }}:
      </span>
      <span
        class="font-medium"
        data-testid="snapshot-fx-override-rate"
      >
        {{ rate.toFixed() }}
      </span>
      <RuiChip
        v-if="hasOverride"
        size="sm"
        color="primary"
        data-testid="snapshot-fx-override-manual"
      >
        {{ t('dashboard.snapshot.detail.fx_override.manual') }}
      </RuiChip>
      <RuiButton
        v-if="!open"
        variant="text"
        size="sm"
        color="primary"
        data-testid="snapshot-fx-override-edit"
        @click="startEdit()"
      >
        {{ t('dashboard.snapshot.detail.fx_override.override') }}
      </RuiButton>
    </div>

    <div
      v-if="open"
      class="mt-2 p-3 rounded-md border border-default bg-rui-grey-50 dark:bg-rui-grey-900 flex flex-col gap-3"
    >
      <div class="flex flex-wrap items-center gap-2">
        <AmountInput
          v-model="input"
          variant="outlined"
          dense
          hide-details
          class="w-48"
          :label="t('dashboard.snapshot.detail.fx_override.rate_label', { symbol: currencySymbol })"
          data-testid="snapshot-fx-override-input"
        />
        <RuiButton
          color="primary"
          size="sm"
          :loading="saving"
          :disabled="!input"
          data-testid="snapshot-fx-override-apply"
          @click="apply()"
        >
          {{ t('common.actions.apply') }}
        </RuiButton>
        <RuiButton
          variant="text"
          size="sm"
          @click="open = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          v-if="hasOverride"
          variant="text"
          size="sm"
          color="error"
          :loading="saving"
          class="ml-auto"
          data-testid="snapshot-fx-override-clear"
          @click="clear()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>
          {{ t('common.actions.clear') }}
        </RuiButton>
      </div>
      <div class="flex items-start gap-1.5 text-caption text-rui-text-secondary">
        <RuiIcon
          name="lu-info"
          size="14"
          class="mt-px shrink-0"
        />
        <span>{{ t('dashboard.snapshot.detail.fx_override.bleed_warning', { symbol: currencySymbol }) }}</span>
      </div>
    </div>
  </div>
</template>
