<script setup lang="ts">
import type { UnusableBinary } from '@shared/starling/binary-types';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useMissingBinaryCopy } from '@/modules/shell/app/use-missing-binary-copy';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';

const { binary } = defineProps<{
  binary: UnusableBinary;
}>();

const { t } = useI18n({ useScope: 'global' });
const { closeApp } = useInterop();

const copy = useMissingBinaryCopy(() => binary);
</script>

<template>
  <ErrorScreen
    class="fixed top-0 left-0 overflow-y-auto justify-center-safe!"
    :header="copy.header"
    :title="copy.title"
    :subtitle="copy.subtitle"
    :message="binary.path"
  >
    <template #details>
      <div class="max-w-2xl mt-6 text-center">
        {{ copy.cause }}
      </div>

      <div
        class="max-w-2xl mt-6 w-full"
        :class="{ 'text-center': copy.steps.length === 0 }"
      >
        <div
          class="font-medium"
          data-testid="missing-binary-recovery"
        >
          {{ copy.recovery }}
        </div>
        <ol
          v-if="copy.steps.length > 0"
          class="list-decimal list-outside pl-5 mt-2 flex flex-col gap-2"
        >
          <li
            v-for="step in copy.steps"
            :key="step"
          >
            {{ step }}
          </li>
        </ol>
      </div>
    </template>

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
