<script setup lang="ts">
defineProps<{
  message?: string;
}>();

const emit = defineEmits<{
  clear: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    type="warning"
    outlined
    class="border border-rui-warning"
  >
    <div class="flex items-start justify-between gap-1">
      <div>
        <div class="font-medium leading-5">
          {{ t('sync_indicator.db_upload_result.title') }}
        </div>
        <div class="text-rui-text-secondary text-sm">
          <i18n-t
            scope="global"
            keypath="sync_indicator.db_upload_result.message"
            tag="span"
          >
            <template #reason>
              <b class="break-words">
                {{ message }}
              </b>
            </template>
          </i18n-t>
        </div>
      </div>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="-mt-1 -mr-1"
        @click="emit('clear')"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
  </RuiAlert>
</template>
