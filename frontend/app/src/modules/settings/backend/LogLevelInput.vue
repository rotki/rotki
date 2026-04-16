<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { LogLevel } from '@shared/log-level';

const model = defineModel<LogLevel>({ required: true });

defineProps<{
  disabled?: boolean;
  successMessages?: string;
  errorMessages?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const levels = Object.values(LogLevel);

const [CreateLabel, ReuseLabel] = createReusableTemplate<{ item: LogLevel }>();

function icon(level: LogLevel): RuiIcons {
  if (level === LogLevel.DEBUG)
    return 'lu-bug';
  else if (level === LogLevel.INFO)
    return 'lu-info';
  else if (level === LogLevel.WARNING)
    return 'lu-triangle-alert';
  else if (level === LogLevel.ERROR)
    return 'lu-circle-alert';
  else if (level === LogLevel.CRITICAL)
    return 'lu-skull';
  else if (level === LogLevel.TRACE)
    return 'lu-file-search';

  throw new Error(`Invalid option: ${level}`);
}
</script>

<template>
  <CreateLabel #default="{ item }">
    <div class="flex items-center gap-3">
      <RuiIcon
        class="text-rui-text-secondary"
        :name="icon(item)"
      />
      <span class="capitalize"> {{ item }} </span>
    </div>
  </CreateLabel>
  <RuiMenuSelect
    v-model="model"
    :options="levels"
    class="loglevel-input"
    :disabled="disabled"
    :label="t('backend_settings.settings.log_level.label')"
    :success-messages="successMessages"
    :error-messages="errorMessages"
    variant="outlined"
  >
    <template #item="{ item }">
      <ReuseLabel :item="item" />
    </template>

    <template #selection="{ item }">
      <ReuseLabel :item="item" />
    </template>
  </RuiMenuSelect>
</template>
