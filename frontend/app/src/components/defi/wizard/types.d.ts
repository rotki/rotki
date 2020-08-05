import { SupportedModules } from '@/services/session/types';

export interface Module {
  name: string;
  icon: string;
  identifier: SupportedModules;
}
