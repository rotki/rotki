import logging
from random import randrange


class LoggingSettings(object):
    __instance = None

    def __new__(cls, anonymized_logs=False):
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = object.__new__(cls)

        LoggingSettings.__instance.anonymized_logs = anonymized_logs
        return LoggingSettings.__instance

    def get():
        if LoggingSettings.__instance is None:
            LoggingSettings.__instance = LoggingSettings()

        return LoggingSettings.__instance


class RotkehlchenLogsAdapter(logging.LoggerAdapter):

    def __init__(self, logger):
        return super().__init__(logger, extra={})

    def process(self, msg, kwargs):
        """
        This is the main post-processing function for Rotkehlchen logs

        It checks if the magive keyword argument 'sensitive_log' is in the kwargs
        and if it is marks the log entry as sensitive. If it is sensitive the values
        of the kwargs are anonymized via the pre-specified rules

        This function also appends all kwargs to the final message.
        """
        settings = LoggingSettings.get()

        is_sensitive = False
        if 'sensitive_log' in kwargs:
            del kwargs['sensitive_log']
            is_sensitive = True

        if is_sensitive and settings.anonymized_logs:
            new_kwargs = {}
            for key, val in kwargs.items():
                new_kwargs[key] = randrange(10)
        else:
            new_kwargs = kwargs

        msg = msg + ','.join(' {}={}'.format(a[0], a[1]) for a in new_kwargs.items())
        return msg, {}
