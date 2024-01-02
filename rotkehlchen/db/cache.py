from rotkehlchen.utils.mixins.enums import Enum


class DBCacheStatic(Enum):
    """It contains all the keys that don't depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_BALANCE_SAVE = 'last_balance_save'
    LAST_DATA_UPLOAD_TS = 'last_data_upload_ts'
    LAST_DATA_UPDATES_TS = 'last_data_updates_ts'
    LAST_OWNED_ASSETS_UPDATE = 'last_owned_assets_update'
    LAST_EVM_ACCOUNTS_DETECT_TS = 'last_evm_accounts_detect_ts'
    LAST_SPAM_ASSETS_DETECT_KEY = 'last_spam_assets_detect_key'
    LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY = 'last_augmented_spam_assets_detect_key'
    LAST_EVENTS_PROCESSING_TASK_TS = 'last_events_processing_task_ts'
    LAST_PRODUCED_BLOCKS_QUERY_TS = 'last_produced_blocks_query_ts'
    LAST_WITHDRAWALS_EXIT_QUERY_TS = 'last_withdrawals_exit_query_ts'


class DBCacheDynamic(Enum):
    """It contains all the formattable keys that depend on a variable
    that can be stored in the `key_value_cache` table"""
    LAST_CRYPTOTX_OFFSET = '{location}_{location_name}_last_cryptotx_offset'
    LAST_QUERY_TS = '{location}_{location_name}_{account_id}_last_query_ts'
    LAST_QUERY_ID = '{location}_{location_name}_{account_id}_last_query_id'
    WITHDRAWALS_TS = 'ethwithdrawalsts_{address}'
    WITHDRAWALS_IDX = 'ethwithdrawalsidx_{address}'

    def get_db_key(self, **kwargs: str) -> str:
        return self.value.format(**kwargs)
