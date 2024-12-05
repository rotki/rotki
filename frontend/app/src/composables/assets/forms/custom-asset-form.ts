import { useForm } from '@/composables/form';

export const useCustomAssetForm = createSharedComposable(useForm<string>);
