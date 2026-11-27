<script setup lang="ts">
import type { AssetVersionUpdate } from '@/modules/assets/types';
import { RuiButton, RuiCard, RuiCheckbox, RuiIcon, RuiTextField } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import StageLayout from '@/modules/auth/stage/StageLayout.vue';

const { versions } = defineProps<{
  versions: AssetVersionUpdate;
}>();

const emit = defineEmits<{
  /** Applies the update, up to the version given; `always` applies later ones without asking. */
  confirm: [choice: { upToVersion: number; always: boolean }];
  /** Skips the update; `remember` keeps it from asking again until a newer version is out. */
  skip: [remember: boolean];
}>();

const { t } = useI18n({ useScope: 'global' });

const showOptions = ref<boolean>(false);
const partial = ref<boolean>(false);
const upToVersion = ref<number>(versions.remote);
const remember = ref<boolean>(false);
const always = ref<boolean>(false);

/** A partial update only makes sense when more than one version is pending. */
const multiple = computed<boolean>(() => versions.remote - versions.local > 1);

const target = computed<number>(() => (get(partial) ? get(upToVersion) : versions.remote));

/** Keeps the typed version inside what this update can stop at, the next version up to the latest. */
function onVersionInput(value: string): void {
  const parsed = Number.parseInt(value);
  const lowest = versions.local + 1;
  if (Number.isNaN(parsed) || parsed < lowest)
    set(upToVersion, lowest);
  else if (parsed > versions.remote)
    set(upToVersion, versions.remote);
  else
    set(upToVersion, parsed);
}

watch(partial, (isPartial) => {
  if (!isPartial)
    set(upToVersion, versions.remote);
});
</script>

<template>
  <StageLayout data-testid="asset-update-prompt">
    <template #title>
      {{ t('unlock_flow.asset_update.prompt.title') }}
    </template>
    <template #subtitle>
      {{ t('unlock_flow.asset_update.prompt.subtitle', { local: versions.local, remote: versions.remote }) }}
    </template>

    <RuiCard
      variant="outlined"
      no-padding
      class="overflow-hidden"
    >
      <div class="p-4 flex items-start gap-3">
        <RuiIcon
          name="lu-database"
          size="20"
          class="shrink-0 mt-0.5 text-rui-primary"
        />
        <div class="min-w-0 flex flex-col gap-0.5">
          <div
            class="text-body-1 font-medium"
            data-testid="asset-update-changes"
          >
            {{ t('unlock_flow.asset_update.prompt.changes', { count: versions.changes }, versions.changes) }}
          </div>
          <div class="text-body-2 text-rui-text-secondary">
            {{ t('unlock_flow.asset_update.range', { from: versions.local, to: target }) }}
          </div>
        </div>
      </div>

      <div class="border-t border-default px-2 py-1">
        <RuiButton
          variant="text"
          color="primary"
          size="sm"
          :aria-expanded="showOptions"
          data-testid="asset-update-options-toggle"
          @click="showOptions = !showOptions"
        >
          <template #append>
            <RuiIcon
              name="lu-chevron-down"
              size="16"
              class="transition-transform"
              :class="{ 'rotate-180': showOptions }"
            />
          </template>
          {{ t('unlock_flow.asset_update.prompt.options') }}
        </RuiButton>
      </div>

      <div
        v-if="showOptions"
        class="px-4 pb-3 flex flex-col"
        data-testid="asset-update-options"
      >
        <template v-if="multiple">
          <RuiCheckbox
            v-model="partial"
            color="primary"
            details="hidden"
            data-testid="asset-update-partial"
          >
            {{ t('unlock_flow.asset_update.prompt.partial') }}
          </RuiCheckbox>
          <RuiTextField
            v-if="partial"
            :model-value="String(upToVersion)"
            class="ml-7 my-2 max-w-48"
            color="primary"
            type="number"
            dense
            details="hidden"
            :min="versions.local + 1"
            :max="versions.remote"
            :label="t('unlock_flow.asset_update.prompt.up_to')"
            data-testid="asset-update-up-to"
            @update:model-value="onVersionInput($event)"
          />
        </template>
        <RuiCheckbox
          v-model="remember"
          color="primary"
          details="hidden"
          data-testid="asset-update-remember"
        >
          {{ t('unlock_flow.asset_update.prompt.remember', { version: versions.remote }) }}
        </RuiCheckbox>
      </div>
    </RuiCard>

    <RuiCheckbox
      v-model="always"
      color="primary"
      :hint="t('unlock_flow.asset_update.prompt.always_hint')"
      details="auto"
      details-under-label
      data-testid="asset-update-always"
    >
      {{ t('unlock_flow.asset_update.prompt.always') }}
    </RuiCheckbox>

    <div class="flex gap-3 text-body-2 text-rui-text-secondary">
      <RuiIcon
        name="lu-info"
        size="20"
        class="shrink-0 mt-0.5 text-rui-primary"
      />
      <p>{{ t('unlock_flow.asset_update.prompt.restart_note') }}</p>
    </div>

    <template #actions>
      <RuiButton
        color="primary"
        data-testid="asset-update-confirm"
        @click="emit('confirm', { always, upToVersion: target })"
      >
        {{ t('unlock_flow.asset_update.prompt.actions.update') }}
      </RuiButton>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="asset-update-skip"
        @click="emit('skip', remember)"
      >
        {{ remember ? t('unlock_flow.asset_update.prompt.actions.skip_version') : t('unlock_flow.asset_update.prompt.actions.skip') }}
      </RuiButton>
    </template>
  </StageLayout>
</template>
