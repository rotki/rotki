import type { ComputedRef } from 'vue';
import type { BlockchainMetadata, TaskMeta } from '@/types/task';
import { get } from '@vueuse/shared';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface BalanceQueryProgress {
  type: TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;
  currentStep: number;
  totalSteps: number;
  percentage: number;
  currentOperation: string | null;
  currentOperationData: {
    type: TaskType.FETCH_DETECTED_TOKENS | TaskType.QUERY_BLOCKCHAIN_BALANCES;
    chain?: string;
    address?: string;
    status: string;
  } | null;
}

interface UseBalanceQueryProgressReturn {
  balanceProgress: ComputedRef<BalanceQueryProgress | null>;
  isBalanceQuerying: ComputedRef<boolean>;
}

interface TokenDetectionMeta extends TaskMeta {
  chain?: string;
  address?: string;
}

// Type guards to safely access meta properties
function isBlockchainMetadata(meta: TaskMeta): meta is BlockchainMetadata {
  return 'blockchain' in meta;
}

function isTokenDetectionMeta(meta: TaskMeta): meta is TokenDetectionMeta {
  return 'chain' in meta || 'address' in meta;
}

// Helper to calculate percentage
function calculatePercentage(current: number, total: number): number {
  return total > 0 ? Math.round((current / total) * 100) : 0;
}

export function useBalanceQueryProgress(): UseBalanceQueryProgressReturn {
  const { t } = useI18n({ useScope: 'global' });
  const taskStore = useTaskStore();
  const { useIsTaskRunning } = taskStore;
  // Use storeToRefs to ensure proper reactivity
  const { tasks } = storeToRefs(taskStore);
  const { massDetecting } = storeToRefs(useBlockchainTokensStore());
  const { addresses } = useAccountAddresses();
  const { getChainName, txEvmChains } = useSupportedChains();

  // Track the last token detection operation to link with subsequent balance query
  const lastTokenDetection = ref<{
    chains: Set<string>;
    totalAddresses: number;
    addressesPerChain: Record<string, number>;
  }>();

  // Track balance queries for chains
  const balanceQueriesInProgress = ref<Set<string>>(new Set());

  const isBalanceQuerying = computed<boolean>(() => get(useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS)) ||
    !!get(massDetecting));

  const balanceProgress = computed<BalanceQueryProgress | null>(() => {
    const taskMap = get(tasks);
    const taskList = Object.values(taskMap);

    // Check for token detection tasks first to see if we're in a unified operation
    const tokenDetectionTasks = taskList.filter(task =>
      task.type === TaskType.FETCH_DETECTED_TOKENS,
    );

    const balanceQueryTasks = taskList.filter(task => task.type === TaskType.QUERY_BLOCKCHAIN_BALANCES);
    const balanceQueryTask = balanceQueryTasks[0]; // Keep for compatibility

    // Check if we have a unified operation (token detection potentially followed by balance query)
    const massDetectingValue = get(massDetecting);
    const addressesPerChain = get(addresses);

    // Track which addresses and chains are actively being detected
    const chainsBeingDetected = new Set<string>();
    const addressesBeingDetectedPerChain: Record<string, Set<string>> = {};
    let totalAddressesBeingDetected = 0;

    for (const task of tokenDetectionTasks) {
      const meta = task.meta;
      if (isTokenDetectionMeta(meta) && meta.chain && meta.address) {
        chainsBeingDetected.add(meta.chain);
        addressesBeingDetectedPerChain[meta.chain] ??= new Set();
        addressesBeingDetectedPerChain[meta.chain].add(meta.address);
        totalAddressesBeingDetected++;
      }
    }

    // Remember this detection for linking with subsequent balance query
    if (chainsBeingDetected.size > 0) {
      const addressCounts = Object.fromEntries(
        Object.entries(addressesBeingDetectedPerChain).map(([chain, addrs]) => [chain, addrs.size]),
      );

      set(lastTokenDetection, {
        addressesPerChain: addressCounts,
        chains: chainsBeingDetected,
        totalAddresses: totalAddressesBeingDetected,
      });
    }

    // Check if balance query is part of token detection flow
    const lastDetection = get(lastTokenDetection);
    const isUnifiedOperation = tokenDetectionTasks.length > 0 ||
      (balanceQueryTask && massDetectingValue) ||
      (balanceQueryTask && lastDetection && isBlockchainMetadata(balanceQueryTask.meta) && lastDetection.chains.has(balanceQueryTask.meta.blockchain || ''));

    if (isUnifiedOperation) {
      // Handle unified token detection + balance query operation
      let totalSteps = 0;
      let currentStep = 0;
      let currentOperation: string;
      let currentOperationData: BalanceQueryProgress['currentOperationData'];
      let currentChain: string | undefined;
      let currentAddress: string | undefined;

      // Calculate total steps for the entire operation
      if (massDetectingValue) {
        // Mass detection mode - count all addresses across all chains
        const chains = massDetectingValue === 'all'
          ? get(txEvmChains).map(chain => chain.id)
          : Array.isArray(massDetectingValue) ? massDetectingValue : [massDetectingValue];

        const totalAddresses = chains.reduce((sum, chain) => {
          return sum + (addressesPerChain[chain]?.length || 0);
        }, 0);

        // Total steps = all addresses + number of chains (for balance queries)
        totalSteps = totalAddresses + chains.length;
      }
      else if (chainsBeingDetected.size > 0) {
        // Individual detection mode - use detected chains and addresses
        totalSteps = totalAddressesBeingDetected + chainsBeingDetected.size;
      }
      else if (balanceQueryTask && lastDetection) {
        // Balance query after token detection - use remembered counts
        totalSteps = lastDetection.totalAddresses + lastDetection.chains.size;
      }

      if (tokenDetectionTasks.length > 0) {
        // Currently detecting tokens - calculate current step across all chains
        let processedAddresses = 0;
        let currentTaskInfo: { chain: string; address: string } | undefined;

        // Count how many addresses have been processed based on what's currently active
        if (massDetectingValue) {
          const chains = massDetectingValue === 'all'
            ? get(txEvmChains).map(chain => chain.id)
            : Array.isArray(massDetectingValue) ? massDetectingValue : [massDetectingValue];

          // Find the first active task to display
          const firstTask = tokenDetectionTasks[0];
          const meta = firstTask.meta;
          if (isTokenDetectionMeta(meta) && meta.chain && meta.address) {
            currentTaskInfo = { address: meta.address, chain: meta.chain };

            // Count completed addresses before this chain
            for (const chain of chains) {
              const chainAddresses = addressesPerChain[chain] || [];
              if (chain === meta.chain) {
                processedAddresses += chainAddresses.indexOf(meta.address);
                break;
              }
              processedAddresses += chainAddresses.length;
            }
          }
        }
        else {
          // Individual detection mode
          const firstTask = tokenDetectionTasks[0];
          const meta = firstTask.meta;
          if (isTokenDetectionMeta(meta) && meta.chain && meta.address) {
            currentTaskInfo = { address: meta.address, chain: meta.chain };

            // Count based on active detections
            const allAddresses = Object.values(addressesBeingDetectedPerChain).flatMap(addrs => Array.from(addrs));
            processedAddresses = allAddresses.indexOf(meta.address);
          }
        }

        currentStep = processedAddresses + 1; // +1 because we're currently processing this address

        if (currentTaskInfo) {
          currentChain = currentTaskInfo.chain;
          currentAddress = currentTaskInfo.address;

          currentOperation = t('dashboard.history_query_indicator.token_detection_status.detecting_with_details', {
            current: currentStep,
            total: totalSteps,
          });

          currentOperationData = {
            address: currentAddress,
            chain: currentChain,
            status: t('dashboard.history_query_indicator.token_detection_status.detecting'),
            type: TaskType.FETCH_DETECTED_TOKENS,
          };
        }
        else {
          // Shouldn't happen, but fallback
          currentStep = 0;
          currentOperation = t('dashboard.history_query_indicator.token_detection_status.detecting');
          currentOperationData = {
            status: t('dashboard.history_query_indicator.token_detection_status.detecting'),
            type: TaskType.FETCH_DETECTED_TOKENS,
          };
        }
      }
      else if (balanceQueryTask) {
        // Token detection finished, now querying balances
        const meta = balanceQueryTask.meta;
        if (isBlockchainMetadata(meta)) {
          currentChain = meta.blockchain;
        }

        if (currentChain && lastDetection) {
          const chainName = get(getChainName(currentChain));

          // Calculate which step we're on based on completed chains
          const completedAddresses = lastDetection.totalAddresses;
          const chainsArray = Array.from(lastDetection.chains);
          const currentChainIndex = chainsArray.indexOf(currentChain);
          const completedChains = currentChainIndex === -1 ? chainsArray.length : currentChainIndex;

          currentStep = completedAddresses + completedChains + 1;

          currentOperation = t('dashboard.history_query_indicator.balance_status.finalizing_chain_balances', {
            chain: chainName,
            current: currentStep,
            total: totalSteps,
          });

          currentOperationData = {
            chain: currentChain,
            status: t('dashboard.history_query_indicator.balance_status.querying_chain_balances', { chain: chainName }),
            type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
          };
        }
        else {
          // Fallback for balance query without proper context
          currentStep = totalSteps;
          currentOperation = t('dashboard.history_query_indicator.balance_status.querying_balances');
          currentOperationData = {
            status: t('dashboard.history_query_indicator.balance_status.querying_balances'),
            type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
          };
        }
      }
      else {
        return null;
      }

      const percentage = calculatePercentage(currentStep, totalSteps);

      return {
        currentOperation,
        currentOperationData,
        currentStep,
        percentage,
        totalSteps,
        type: tokenDetectionTasks.length > 0 ? TaskType.FETCH_DETECTED_TOKENS : TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };
    }

    // Clear last detection if balance query completes
    if (!balanceQueryTask && tokenDetectionTasks.length === 0 && lastDetection) {
      set(lastTokenDetection, undefined);
    }

    // Handle standalone balance query (not part of token detection flow)
    if (balanceQueryTasks.length > 0 && !isUnifiedOperation) {
      // Track all chains being queried currently
      const chainsBeingQueried = new Set<string>();
      let currentChain: string | undefined;

      for (const task of balanceQueryTasks) {
        const meta = task.meta;
        if (isBlockchainMetadata(meta) && meta.blockchain) {
          chainsBeingQueried.add(meta.blockchain);
          currentChain ??= meta.blockchain; // Use first task's chain as current
        }
      }

      // For standalone balance queries without a clear total, we can only track what we see
      // We'll track the first batch of chains and assume that's the total
      const previousTracking = get(balanceQueriesInProgress);

      // Detect if this is a new operation by checking if we have a clean slate
      // (no previous tracking) or if the first chain being queried wasn't in the previous set
      const firstChainInBatch = Array.from(chainsBeingQueried)[0];
      const isNewOperation = previousTracking.size === 0 ||
        (firstChainInBatch && !previousTracking.has(firstChainInBatch));

      if (isNewOperation) {
        // New operation - reset and track from scratch
        // We'll discover the total as chains get queried
        set(balanceQueriesInProgress, new Set());
      }

      // Add currently queried chains to our tracking
      const updatedTracking = new Set(get(balanceQueriesInProgress));
      chainsBeingQueried.forEach(chain => updatedTracking.add(chain));
      set(balanceQueriesInProgress, updatedTracking);

      // The total is all chains we've seen so far in this operation
      const totalSteps = updatedTracking.size;

      // Current step is how many chains we've seen minus what's currently active
      const completedChains = updatedTracking.size - chainsBeingQueried.size;
      const currentStep = completedChains;

      let operationText: string;
      if (currentChain) {
        const chainName = get(getChainName(currentChain));
        if (totalSteps > 1) {
          operationText = t('dashboard.history_query_indicator.balance_status.querying_chain_balances_with_progress', {
            chain: chainName,
            current: currentStep,
            total: totalSteps,
          });
        }
        else {
          operationText = t('dashboard.history_query_indicator.balance_status.querying_chain_balances', {
            chain: chainName,
          });
        }
      }
      else {
        operationText = t('dashboard.history_query_indicator.balance_status.querying_balances');
      }

      const percentage = calculatePercentage(currentStep, totalSteps);

      return {
        currentOperation: operationText,
        currentOperationData: {
          chain: currentChain,
          status: operationText,
          type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        },
        currentStep,
        percentage,
        totalSteps,
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      };
    }

    // Clear balance queries tracking when done
    if (balanceQueryTasks.length === 0 && get(balanceQueriesInProgress).size > 0) {
      set(balanceQueriesInProgress, new Set());
    }

    return null;
  });

  return {
    balanceProgress,
    isBalanceQuerying,
  };
}
