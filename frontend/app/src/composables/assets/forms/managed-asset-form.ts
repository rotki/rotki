import { useForm } from '@/composables/form';

export const useManagedAssetForm = createSharedComposable(useForm<boolean>);
