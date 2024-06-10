<script setup lang="ts">
import { useAppRoutes } from '@/router/routes';
import { NoteLocation } from '@/types/notes';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', visible: boolean): void;
  (e: 'about'): void;
}>();

const { t } = useI18n();

const display = useVModel(props, 'visible', emit);

const tab = ref<number>(0);

const route = useRoute();

const { openDialog } = useUserNotesForm();

const location = computed<string>(() => {
  const meta = get(route).meta;

  if (meta && meta.noteLocation)
    return meta.noteLocation;

  let noteLocation = '';
  get(route).matched.forEach((matched) => {
    if (matched.meta.noteLocation)
      noteLocation = matched.meta.noteLocation;
  });

  return noteLocation;
});

const { appRoutes } = useAppRoutes();

function getNoteLocationKey(key: string): string | null {
  const index = Object.values<string>(NoteLocation).indexOf(key);
  if (index > -1)
    return Object.keys(NoteLocation)[index];

  return null;
}

const locationName = computed<string>(() => {
  const locationVal = get(location);
  if (!locationVal)
    return '';

  const noteLocationKey = getNoteLocationKey(locationVal);
  if (!noteLocationKey)
    return '';

  const Routes = get(appRoutes);
  const keyIn = (key: string): key is keyof typeof Routes => key in Routes;

  if (keyIn(noteLocationKey))
    return Routes[noteLocationKey].text;

  return '';
});

watch(locationName, (locationName) => {
  if (locationName === '')
    set(tab, 0);
});
</script>

<template>
  <RuiNavigationDrawer
    v-model="display"
    width="460px"
    temporary
    :stateless="openDialog"
    position="right"
  >
    <div
      class="flex items-center justify-between gap-2 w-full border-b border-default"
    >
      <RuiTabs
        v-model="tab"
        class="tabs"
        color="primary"
      >
        <template #default>
          <RuiTab>
            {{ t('notes_menu.tabs.general') }}
          </RuiTab>
          <RuiTab v-if="locationName">
            <RuiTooltip
              :popper="{ placement: 'bottom' }"
              :open-delay="400"
            >
              <template #activator>
                {{ t('notes_menu.tabs.in_this_page', { page: locationName }) }}
              </template>
              {{
                t('notes_menu.tabs.in_this_page_tooltip', {
                  page: locationName,
                })
              }}
            </RuiTooltip>
          </RuiTab>
        </template>
      </RuiTabs>

      <RuiButton
        class="!p-2"
        variant="text"
        icon
        @click="display = false"
      >
        <RuiIcon name="close-line" />
      </RuiButton>
    </div>

    <UserNotesList
      v-if="visible"
      :key="location + tab"
      :location="tab === 0 ? '' : location"
    />
  </RuiNavigationDrawer>
</template>
