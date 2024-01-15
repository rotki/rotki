import type { Blockchain } from '@rotki/common/lib/blockchain';
import type { MaybeRef } from '@vueuse/shared';

type FormComposable = ReturnType<typeof useForm<boolean>>;
let rpcForms: Record<string, () => FormComposable> | undefined;

export function useEvmRpcNodeForm(chain: MaybeRef<Blockchain>): FormComposable {
  const blockchain = get(chain);

  if (rpcForms?.[blockchain])
    return rpcForms[blockchain]();

  const composable = createSharedComposable(useForm<boolean>);

  if (!rpcForms)
    rpcForms = {};

  rpcForms[blockchain] = composable;

  return composable();
}

/**
 * TODO: remove and change the whole logic here
 */
export function disposeEvmRpcNodeComposables() {
  rpcForms = undefined;
}
