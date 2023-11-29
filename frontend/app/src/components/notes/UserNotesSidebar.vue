<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import { NoteLocation } from '@/types/notes';

defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'visible:update', visible: boolean): void;
  (e: 'about'): void;
}>();

const { t } = useI18n();

const tab = ref<number>(0);
const visibleUpdate = (_visible: boolean) => {
  emit('visible:update', _visible);
};

const route = useRoute();

const location = computed<string>(() => {
  const meta = get(route).meta;

  if (meta && meta.noteLocation) {
    return meta.noteLocation;
  }

  let noteLocation = '';
  get(route).matched.forEach(matched => {
    if (matched.meta.noteLocation) {
      noteLocation = matched.meta.noteLocation;
    }
  });

  return noteLocation;
});

const { appRoutes } = useAppRoutes();

const getNoteLocationKey = (key: string): string | null => {
  const index = Object.values<string>(NoteLocation).indexOf(key);
  if (index > -1) {
    return Object.keys(NoteLocation)[index];
  }

  return null;
};

const locationName = computed<string>(() => {
  const locationVal = get(location);
  if (!locationVal) {
    return '';
  }

  const noteLocationKey = getNoteLocationKey(locationVal);
  if (!noteLocationKey) {
    return '';
  }

  const Routes = get(appRoutes);
  const keyIn = (key: string): key is keyof typeof Routes => key in Routes;

  if (keyIn(noteLocationKey)) {
    return Routes[noteLocationKey].text;
  }

  return '';
});

watch(locationName, locationName => {
  if (locationName === '') {
    set(tab, 0);
  }
});

const { smAndDown } = useDisplay();
</script>

<template>
  <VNavigationDrawer
    width="400px"
    class="user-notes-sidebar"
    :class="smAndDown ? 'user-notes-sidebar--mobile' : null"
    absolute
    clipped
    :value="visible"
    right
    temporary
    hide-overlay
    @input="visibleUpdate($event)"
  >
    <div
      class="flex items-center justify-between gap-2 w-full border-b border-default"
    >
      <RuiTabs v-model="tab" class="tabs" color="primary">
        <template #default>
          <RuiTab>
            {{ t('notes_menu.tabs.general') }}
          </RuiTab>
          <RuiTab v-if="locationName">
            <RuiTooltip :popper="{ placement: 'bottom' }" open-delay="400">
              <template #activator>
                {{ t('notes_menu.tabs.in_this_page', { page: locationName }) }}
              </template>
              {{
                t('notes_menu.tabs.in_this_page_tooltip', {
                  page: locationName
                })
              }}
            </RuiTooltip>
          </RuiTab>
        </template>
      </RuiTabs>

      <RuiButton class="!p-2" variant="text" icon @click="visibleUpdate(false)">
        <RuiIcon name="close-line" />
      </RuiButton>
    </div>

    <UserNotesList
      :key="location + tab"
      :location="tab === 0 ? '' : location"
    />
  </VNavigationDrawer>
</template>

<style lang="scss" scoped>
.user-notes-sidebar {
  top: 64px !important;
  box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1);
  padding-top: 0 !important;
  border-top: var(--v-rotki-light-grey-darken1) solid thin;

  &--mobile {
    top: 56px !important;
  }

  &.v-navigation-drawer {
    &--is-mobile {
      padding-top: 0 !important;
    }
  }
}

.tabs {
  :deep(.v-slide-group) {
    .v-slide-group {
      &__prev,
      &__next {
        display: none;
      }

      &__wrapper {
        .v-tab {
          font-size: 0.75rem;
          padding: 0 1rem;
          margin-left: 0;
          flex: none;
          width: auto;
        }
      }
    }
  }
}
</style>
