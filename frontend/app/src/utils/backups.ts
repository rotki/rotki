import { type Ref } from 'vue';
import { type UserDbBackup } from '@/types/backup';

export const getFilepath = (
  db: UserDbBackup,
  directory: Ref<string>
): string => {
  const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
  return `${directory.value}${file}`;
};
