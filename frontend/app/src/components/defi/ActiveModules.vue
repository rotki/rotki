<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import QueriedAddressDialog from '@/components/defi/QueriedAddressDialog.vue';
import { useConfirmStore } from '@/store/confirm';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';
import { assert, type Nullable } from '@rotki/common';

interface ModuleWithStatus {
  readonly identifier: Module;
  readonly enabled: boolean;
}

const props = defineProps<{
  modules: Module[];
}>();

const { modules } = toRefs(props);
const manageModule = ref<Nullable<Module>>(null);
const confirmEnable = ref<Nullable<Module>>(null);

const supportedModules = SUPPORTED_MODULES;

const { fetchQueriedAddresses } = useQueriedAddressesStore();
const { update } = useSettingsStore();
const { activeModules } = storeToRefs(useGeneralSettingsStore());

const moduleStatus = computed(() => {
  const active = get(activeModules);
  return get(modules)
    .map(module => ({
      enabled: active.includes(module),
      identifier: module,
    }))
    .sort((a, b) => (a.enabled === b.enabled ? 0 : a.enabled ? -1 : 1));
});

function onModulePress(module: ModuleWithStatus) {
  if (module.enabled) {
    set(manageModule, module.identifier);
  }
  else {
    showConfirmation();
    set(confirmEnable, module.identifier);
  }
}

async function enableModule() {
  const module = get(confirmEnable);
  assert(module !== null);
  await update({
    activeModules: [...get(activeModules), module],
  });
  set(confirmEnable, null);
}

function name(module: string): string {
  const data = supportedModules.find(value => value.identifier === module);
  return data?.name ?? '';
}

function icon(module: Module): string {
  const data = supportedModules.find(value => value.identifier === module);
  return data?.icon ?? '';
}

const { t } = useI18n();

function getName(module: Nullable<Module>) {
  return {
    name: module ? name(module) : '',
  };
}

onMounted(async () => {
  await fetchQueriedAddresses();
});

const { show } = useConfirmStore();

function showConfirmation() {
  show(
    {
      message: t('active_modules.enable.description', getName(get(confirmEnable))),
      title: t('active_modules.enable.title'),
      type: 'info',
    },
    enableModule,
  );
}
</script>

<template>
  <div>
    <RuiCard
      no-padding
      class="px-1 py-0.5 bg-white dark:bg-rui-grey-900"
      content-class="flex items-center justify-center"
    >
      <div
        v-for="module in moduleStatus"
        :key="module.identifier"
        class="flex"
      >
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              variant="text"
              icon
              size="sm"
              :class="module.enabled ? null : 'grayscale'"
              @click="onModulePress(module)"
            >
              <AppImage
                width="24px"
                height="24px"
                contain
                :src="icon(module.identifier)"
              />
            </RuiButton>
          </template>
          <span v-if="module.enabled">
            {{ t('active_modules.view_addresses', getName(module.identifier)) }}
          </span>
          <span v-else>
            {{ t('active_modules.activate', getName(module.identifier)) }}
          </span>
        </RuiTooltip>
      </div>
    </RuiCard>
    <QueriedAddressDialog
      v-if="manageModule"
      :module="manageModule"
      @close="manageModule = null"
    />
  </div>
</template>
