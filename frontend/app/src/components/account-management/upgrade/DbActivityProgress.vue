<script setup lang="ts">
import { type CurrentDbUpgradeProgress } from '@/types/login';

const props = withDefaults(
  defineProps<{
    progress: CurrentDbUpgradeProgress | null;
    dataMigration?: boolean;
  }>(),
  {
    dataMigration: false
  }
);

const { progress } = toRefs(props);

const { tc } = useI18n();

const multipleUpgrades = computed(() => {
  if (isDefined(progress)) {
    const { toVersion, fromVersion } = get(progress);
    return toVersion - fromVersion > 1;
  }
  return false;
});
</script>

<template>
  <card v-if="progress" flat>
    <template #title>
      <span v-if="dataMigration">{{ tc('login.migrating_data.title') }} </span>
      <span v-else> {{ tc('login.upgrading_db.title') }}</span>
    </template>
    <v-row class="my-2">
      <v-col cols="auto">
        <div class="mr-2">
          <v-progress-circular
            rounded
            :value="progress.percentage"
            size="45"
            width="4"
            color="primary"
          >
            <div v-if="multipleUpgrades">
              <v-progress-circular
                :value="progress.totalPercentage"
                color="primary"
              />
            </div>
          </v-progress-circular>
        </div>
      </v-col>
      <v-col class="text-body-1">
        <div v-if="!dataMigration">
          <div>
            {{ tc('login.upgrading_db.warning', 0, progress) }}
          </div>
          <v-divider class="my-2" />
          <div>
            {{ tc('login.upgrading_db.current', 0, progress) }}
          </div>
        </div>
        <div v-else>
          <div>
            {{ tc('login.migrating_data.warning', 0, progress) }}
          </div>
          <v-divider class="my-2" />
          <div>
            {{ tc('login.migrating_data.current', 0, progress) }}
          </div>
          <ul v-if="progress.description" class="ml-n2">
            <li>{{ progress.description }}</li>
          </ul>
        </div>
      </v-col>
    </v-row>
  </card>
</template>
