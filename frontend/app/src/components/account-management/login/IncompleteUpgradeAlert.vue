<script setup lang="ts">
const emit = defineEmits<{ (e: 'confirm'): void; (e: 'cancel'): void }>();

const { t } = useI18n();

const { incompleteUpgradeConflict } = storeToRefs(useSessionAuthStore());
</script>

<template>
  <Transition>
    <LoginActionAlert
      v-if="incompleteUpgradeConflict"
      icon="alert-line"
      @confirm="emit('confirm')"
      @cancel="emit('cancel')"
    >
      <template #title>
        {{ t('login.incomplete_upgrade_error.title') }}
      </template>
      <template #cancel>
        {{ t('login.incomplete_upgrade_error.abort') }}
      </template>
      <template #confirm>
        {{ t('login.incomplete_upgrade_error.resume') }}
      </template>

      <div>{{ incompleteUpgradeConflict.message }}</div>
      <div class="mt-2">
        {{ t('login.incomplete_upgrade_error.question') }}
      </div>
    </LoginActionAlert>
  </Transition>
</template>
