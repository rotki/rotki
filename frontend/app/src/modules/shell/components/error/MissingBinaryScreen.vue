<script setup lang="ts">
import { BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';

const { binary } = defineProps<{
  binary: UnusableBinary;
}>();

const { t } = useI18n({ useScope: 'global' });
const { closeApp } = useInterop();

const isMissing = computed<boolean>(() => binary.status === BinaryStatus.MISSING);

const header = computed<string>(() => get(isMissing)
  ? t('missing_binary.header')
  : t('missing_binary.header_not_executable'));

const title = computed<string>(() => get(isMissing)
  ? t('missing_binary.missing', { component: binary.component })
  : t('missing_binary.not_executable', { component: binary.component }));
</script>

<template>
  <ErrorScreen
    class="fixed top-0 left-0 overflow-y-auto ![justify-content:safe_center]"
    :header="header"
    :title="title"
    :subtitle="t('missing_binary.subtitle')"
    :message="binary.path"
  >
    <div class="max-w-2xl mt-6 text-center">
      {{ t('missing_binary.cause') }}
    </div>

    <div class="max-w-2xl mt-6 w-full">
      <div class="font-medium">
        {{ t('missing_binary.recovery') }}
      </div>
      <ol class="list-decimal list-outside pl-5 mt-2 flex flex-col gap-2">
        <li>{{ t('missing_binary.steps.update_definitions') }}</li>
        <li>
          {{ t('missing_binary.steps.restore') }}
          <template v-if="binary.onWindows">
            {{ t('missing_binary.steps.restore_windows') }}
          </template>
        </li>
        <li>{{ t('missing_binary.steps.exclude') }}</li>
        <li>{{ t('missing_binary.steps.reinstall') }}</li>
      </ol>
    </div>

    <template #bottom>
      <RuiButton
        depressed
        color="primary"
        data-testid="missing-binary-terminate"
        @click="closeApp()"
      >
        {{ t('common.actions.terminate') }}
      </RuiButton>
    </template>
  </ErrorScreen>
</template>
