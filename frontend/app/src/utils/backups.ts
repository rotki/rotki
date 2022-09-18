import { Ref } from 'vue';
import { UserDbBackup } from '@/types/backup';

export const getFilepath = (db: UserDbBackup, directory: Ref<string>) => {
  const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
  return `${directory.value}${file}`;
};
