<script setup lang="ts">
interface UserDbInfo {
  version: string;
  size: string;
}

interface GlobalDbInfo {
  schema: string;
  assets: string;
}

const props = defineProps<{
  directory: string;
  globalDb: GlobalDbInfo;
  userDb: UserDbInfo;
}>();

const { t } = useI18n();

const userDetails = computed(() => [
  {
    value: props.directory,
    label: t('database_info_display.directory'),
    copiable: true
  },
  {
    value: props.userDb.version,
    label: t('database_info_display.userdb_version')
  },
  {
    value: props.userDb.size,
    label: t('database_info_display.userdb_size')
  }
]);

const globalDetails = computed(() => [
  {
    value: props.globalDb.schema,
    label: t('database_info_display.globaldb_schema')
  },
  {
    value: props.globalDb.assets,
    label: t('database_info_display.globaldb_assets')
  }
]);

const [DefineRow, ReuseRow] = createReusableTemplate<{
  label: string;
  value: string;
}>();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('database_info_display.title') }}
    </template>

    <DefineRow #default="{ label, value, copiable }">
      <div class="flex gap-4 items-center">
        <span class="font-bold min-w-[9rem]">
          {{ label }}
        </span>
        <span
          class="flex-1 text-rui-text-secondary overflow-hidden flex items-center gap-2"
        >
          <span :title="value" class="text-truncate">{{ value }}</span>
          <CopyButton
            v-if="copiable"
            size="sm"
            :tooltip="value"
            :value="value"
          />
        </span>
      </div>
    </DefineRow>

    <div class="grid md:grid-cols-2 gap-4">
      <div class="overflow-hidden">
        <div class="font-bold text-h6 mb-2">
          {{ t('database_info_display.userdb') }}
        </div>

        <ReuseRow
          v-for="(detail, index) in userDetails"
          :key="index"
          v-bind="detail"
        />
      </div>
      <div class="overflow-hidden">
        <div class="font-bold text-h6 mb-2">
          {{ t('database_info_display.globaldb') }}
        </div>

        <ReuseRow
          v-for="(detail, index) in globalDetails"
          :key="index"
          v-bind="detail"
        />
      </div>
    </div>
  </RuiCard>
</template>
