import { type ComputedRef, type Ref } from 'vue';
import {
  AIRDROP_POAP,
  type Airdrop,
  type AirdropDetail,
  type AirdropType,
  Airdrops,
  type PoapDelivery
} from '@/types/airdrops';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useAirdropStore = defineStore('defi/airdrops', () => {
  const airdrops: Ref<Airdrops> = ref({});

  const { fetchAirdrops: fetchAirdropsCaller } = useDefiApi();

  const airdropAddresses = computed(() => Object.keys(get(airdrops)));

  const { t } = useI18n();

  const { awaitTask } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { setStatus, fetchDisabled } = useStatusUpdater(Section.DEFI_AIRDROPS);

  const airdropList = (addresses: string[]): ComputedRef<Airdrop[]> =>
    computed(() => {
      const result: Airdrop[] = [];
      const data = get(airdrops);
      for (const address in data) {
        if (addresses.length > 0 && !addresses.includes(address)) {
          continue;
        }
        const airdrop = data[address];
        for (const source in airdrop) {
          const element = airdrop[source];
          if (source === AIRDROP_POAP) {
            const details = element as PoapDelivery[];
            result.push({
              address,
              source: source as AirdropType,
              details: details.map(value => ({
                amount: bigNumberify('1'),
                link: value.link,
                name: value.name,
                event: value.event
              }))
            });
          } else {
            const { amount, asset, link } = element as AirdropDetail;
            result.push({
              address,
              amount,
              link,
              source: source as AirdropType,
              asset
            });
          }
        }
      }
      return result;
    });

  async function fetchAirdrops(refresh = false) {
    if (fetchDisabled(refresh)) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus);

    try {
      const { taskId } = await fetchAirdropsCaller();
      const { result } = await awaitTask<Airdrops, TaskMeta>(
        taskId,
        TaskType.DEFI_AIRDROPS,
        {
          title: t('actions.defi.airdrops.task.title').toString()
        }
      );
      set(airdrops, Airdrops.parse(result));
    } catch (e: any) {
      logger.error(e);
      notify({
        title: t('actions.defi.airdrops.error.title').toString(),
        message: t('actions.defi.airdrops.error.description', {
          error: e.message
        }).toString(),
        display: true
      });
    }
    setStatus(Status.LOADED);
  }

  return {
    airdrops,
    airdropAddresses,
    airdropList,
    fetchAirdrops
  };
});
