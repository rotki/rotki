<script setup lang="ts">
import type { Filters } from '@/modules/core/table/filters/use-assets-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType, isIgnoredAssetsHandling } from '@/modules/assets/types';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import IgnoreButtons from '@/modules/history/IgnoreButtons.vue';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

const ignoredFilter = defineModel<IgnoredFilter>('ignoredFilter', { required: true });
const selected = defineModel<string[]>('selected', { required: true });
const filtersModel = defineModel<Filters>('matches', { required: true });

const { spamDisabled = false } = defineProps<{
  fields: FieldDef[];
  spamDisabled?: boolean;
}>();

const emit = defineEmits<{
  'ignore': [ignored: boolean];
  'mark-spam': [];
  'refresh:ignored': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const pillLabels = usePillBarLabels();

const disabledIgnoreActions = computed<{ ignore: boolean; unIgnore: boolean }>(() => {
  const { ignoredAssetsHandling } = get(ignoredFilter);
  return {
    ignore: ignoredAssetsHandling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE,
  };
});

// The owned, whitelisted and ignored filters are param-bound pills in the bar (paramKeys
// `showUserOwnedAssetsOnly`, `showWhitelistedAssetsOnly`, `ignoredAssetsHandling`). Bridge the
// bar's param bag to the model backing them, so the bar drives the same source the status dropdown
// used to. An absent param clears its part of the model: removing the pill is how the filter is
// turned off, and for the ignored handling "off" is the table's default, `exclude`.
const pillParams = computed<Record<string, string | string[] | boolean>>({
  get(): Record<string, string | string[] | boolean> {
    const { ignoredAssetsHandling, onlyShowOwned, onlyShowWhitelisted } = get(ignoredFilter);
    return {
      ...(onlyShowOwned ? { showUserOwnedAssetsOnly: true } : {}),
      ...(onlyShowWhitelisted ? { showWhitelistedAssetsOnly: true } : {}),
      ...(ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE ? {} : { ignoredAssetsHandling }),
    };
  },
  set(value: Record<string, string | string[] | boolean>): void {
    const handling = value.ignoredAssetsHandling;
    set(ignoredFilter, {
      ignoredAssetsHandling: typeof handling === 'string' && isIgnoredAssetsHandling(handling)
        ? handling
        : IgnoredAssetHandlingType.EXCLUDE,
      onlyShowOwned: value.showUserOwnedAssetsOnly === true,
      onlyShowWhitelisted: value.showWhitelistedAssetsOnly === true,
    });
  },
});

function clearSelection() {
  set(selected, []);
}

function handleIgnore(ignored: boolean): void {
  emit('ignore', ignored);
}

function handleMarkSpam(): void {
  emit('mark-spam');
}

// The ignored list is what the "only ignored" filter shows, and it is only fetched on demand, so
// asking for it has to be what refreshes it. The radio group used to say so itself; now the pill
// does, and the request follows from the value rather than from the control that set it.
watch(() => get(ignoredFilter).ignoredAssetsHandling, (handling) => {
  if (handling === IgnoredAssetHandlingType.SHOW_ONLY)
    emit('refresh:ignored');
});
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 mb-4">
    <div class="flex gap-3">
      <IgnoreButtons
        :disabled="selected.length === 0"
        :disabled-actions="disabledIgnoreActions"
        @ignore="handleIgnore($event)"
      />
      <div class="border-l border-default pl-3">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              class="min-w-[5.625rem]"
              variant="outlined"
              color="error"
              :disabled="selected.length === 0 || spamDisabled"
              @click="handleMarkSpam()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-trash-2"
                  size="16"
                />
              </template>
              {{ t('asset_table.mark_spam') }}
            </RuiButton>
          </template>
          <span>{{ t('asset_table.mark_spam_tooltip') }}</span>
        </RuiTooltip>
      </div>
      <div
        v-if="selected.length > 0"
        class="flex gap-2 items-center text-sm"
      >
        {{ t('asset_table.selected', { count: selected.length }) }}
        <RuiButton
          size="sm"
          class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
          @click="clearSelection()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </template>
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </div>

    <PillFilterBar
      v-model:matches="filtersModel"
      v-model:params="pillParams"
      class="flex-1 min-w-[12rem] lg:min-w-[24rem]"
      :fields="fields"
      :labels="pillLabels"
    />
  </div>
</template>
