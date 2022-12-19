import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Message } from '@rotki/common/lib/messages';
import {
  type Eth2ValidatorEntry,
  type Eth2Validators
} from '@rotki/common/lib/staking/eth2';
import { type ComputedRef, type Ref } from 'vue';
import { type GeneralAccountData } from '@/services/types-api';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { type Eth2Validator } from '@/types/balances';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { removeTags } from '@/utils/tags';
import { useBlockchainAccountsApi } from '@/services/accounts';

const defaultValidators = (): Eth2Validators => ({
  entries: [],
  entriesFound: 0,
  entriesLimit: 0
});

export const useEthAccountsStore = defineStore(
  'blockchain/accounts/eth',
  () => {
    const eth: Ref<GeneralAccountData[]> = ref([]);
    const eth2Validators: Ref<Eth2Validators> = ref(defaultValidators());

    const { awaitTask } = useTasks();
    const { activeModules } = storeToRefs(useGeneralSettingsStore());
    const { notify } = useNotificationsStore();
    const { setMessage } = useMessageStore();
    const { t, tc } = useI18n();

    const {
      getEth2Validators,
      addEth2Validator: addEth2ValidatorCaller,
      editEth2Validator: editEth2ValidatorCaller,
      deleteEth2Validators: deleteEth2ValidatorsCaller
    } = useBlockchainAccountsApi();

    const fetchEth2Validators = async () => {
      if (!get(activeModules).includes(Module.ETH2)) {
        return;
      }
      try {
        const validators = await getEth2Validators();
        set(eth2Validators, validators);
      } catch (e: any) {
        logger.error(e);
        notify({
          title: tc('actions.get_accounts.error.title'),
          message: tc('actions.get_accounts.error.description', 0, {
            blockchain: Blockchain.ETH2,
            message: e.message
          }).toString(),
          display: true
        });
      }
    };

    const addEth2Validator = async (
      payload: Eth2Validator
    ): Promise<boolean> => {
      const { activeModules } = useGeneralSettingsStore();
      if (!get(activeModules).includes(Module.ETH2)) {
        return false;
      }
      const id = payload.publicKey || payload.validatorIndex;
      try {
        const taskType = TaskType.ADD_ETH2_VALIDATOR;
        const { taskId } = await addEth2ValidatorCaller(payload);
        const { result } = await awaitTask<boolean, TaskMeta>(
          taskId,
          taskType,
          {
            title: tc('actions.add_eth2_validator.task.title'),
            description: tc('actions.add_eth2_validator.task.description', 0, {
              id
            })
          }
        );
        if (result) {
          const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);
          resetStatus();
          resetStatus(Section.STAKING_ETH2_DEPOSITS);
          resetStatus(Section.STAKING_ETH2_STATS);
        }

        return result;
      } catch (e: any) {
        logger.error(e);
        setMessage({
          description: t('actions.add_eth2_validator.error.description', {
            id,
            message: e.message
          }).toString(),
          title: t('actions.add_eth2_validator.error.title').toString(),
          success: false
        });
        return false;
      }
    };

    const editEth2Validator = async (
      payload: Eth2Validator
    ): Promise<boolean> => {
      const { activeModules } = useGeneralSettingsStore();
      if (!get(activeModules).includes(Module.ETH2)) {
        return false;
      }

      const id = payload.validatorIndex;
      try {
        const success = await editEth2ValidatorCaller(payload);

        if (success) {
          const { resetStatus } = useStatusUpdater(Section.STAKING_ETH2);
          resetStatus();
          resetStatus(Section.STAKING_ETH2_DEPOSITS);
          resetStatus(Section.STAKING_ETH2_STATS);
        }

        return success;
      } catch (e: any) {
        logger.error(e);
        const message: Message = {
          description: t('actions.edit_eth2_validator.error.description', {
            id,
            message: e.message
          }).toString(),
          title: t('actions.edit_eth2_validator.error.title').toString(),
          success: false
        };
        await setMessage(message);
        return false;
      }
    };

    const deleteEth2Validators = async (validators: string[]) => {
      try {
        const validatorsState = get(eth2Validators);
        const entries = [...validatorsState.entries];
        const cachedValidators = entries.filter(({ publicKey }) =>
          validators.includes(publicKey)
        );
        const success = await deleteEth2ValidatorsCaller(cachedValidators);
        if (success) {
          const remainingValidators = entries.filter(
            ({ publicKey }) => !validators.includes(publicKey)
          );
          const data: Eth2Validators = {
            entriesLimit: validatorsState.entriesLimit,
            entriesFound: remainingValidators.length,
            entries: remainingValidators
          };
          set(eth2Validators, data);
        }
        return success;
      } catch (e: any) {
        logger.error(e);
        setMessage({
          description: t('actions.delete_eth2_validator.error.description', {
            message: e.message
          }).toString(),
          title: t('actions.delete_eth2_validator.error.title').toString(),
          success: false
        });
        return false;
      }
    };

    const getEth2Account = (publicKey: string) =>
      computed(() => {
        const validator = get(eth2Validators).entries.find(
          (eth2Validator: Eth2ValidatorEntry) =>
            eth2Validator.publicKey === publicKey
        );

        if (!validator) return undefined;

        return {
          address: validator.publicKey,
          label: validator.validatorIndex.toString() ?? '',
          tags: [],
          chain: Blockchain.ETH2
        };
      });

    const updateEth = (data: GeneralAccountData[]) => {
      set(eth, data);
    };

    const removeTag = (tag: string) => {
      set(eth, removeTags(get(eth), tag));
    };

    const ethAddresses: ComputedRef<string[]> = computed(() => {
      return get(eth).map(({ address }) => address);
    });

    return {
      eth,
      ethAddresses,
      eth2Validators,
      getEth2Account,
      addEth2Validator,
      editEth2Validator,
      deleteEth2Validators,
      fetchEth2Validators,
      updateEth,
      removeTag
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEthAccountsStore, import.meta.hot));
}
