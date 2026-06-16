from typing import Final, Literal

LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
# How aggressively the analytics layer strips identifiers before data reaches the LLM:
# - ``strict``:   hash every identifier, label and name; redact all free text.
# - ``balanced``: hash addresses/tx hashes/group ids, but keep human-friendly account
#                 labels (e.g. exchange-account names) that are not themselves addresses.
# - ``raw``:      no filtering. Must be opted into explicitly at server start.
PrivacyMode = Literal['balanced', 'strict', 'raw']

SERVICE_NAME: Final = 'rotki MCP'
