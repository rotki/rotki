import { useForm } from '@/composables/form';

export const useAccountingRuleForm = createSharedComposable(useForm<boolean>);
