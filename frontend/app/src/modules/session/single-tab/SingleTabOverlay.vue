<script setup lang="ts">
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useSingleTab } from '@/modules/session/single-tab/use-single-tab';

const { t } = useI18n({ useScope: 'global' });

const { isActiveTab, reclaim } = useSingleTab();
const { logged } = storeToRefs(useSessionAuthStore());

const visible = computed<boolean>(() => get(logged) && !get(isActiveTab));
</script>

<template>
  <Transition
    enter-from-class="opacity-0"
    enter-to-class="opacity-1"
    enter-active-class="transition duration-300"
    leave-from-class="opacity-1"
    leave-to-class="opacity-0"
    leave-active-class="transition duration-100"
  >
    <div
      v-if="visible"
      class="fixed top-0 left-0 w-full h-full bg-white dark:bg-rui-grey-900 z-[9999] flex items-center justify-center p-4"
    >
      <div class="flex flex-col gap-6 justify-center items-center max-w-md text-center">
        <RuiIcon
          name="lu-app-window"
          size="48"
          class="text-rui-text-secondary"
        />
        <div class="flex flex-col gap-2">
          <h4 class="text-h6 text-rui-text">
            {{ t('single_tab.title') }}
          </h4>
          <p class="mb-0 text-rui-text-secondary">
            {{ t('single_tab.message') }}
          </p>
        </div>
        <RuiButton
          color="primary"
          @click="reclaim()"
        >
          {{ t('single_tab.action') }}
        </RuiButton>
      </div>
    </div>
  </Transition>
</template>
