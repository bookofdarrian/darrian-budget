import sys
sys.path.insert(0, '.')
from utils.db import init_db, set_setting
init_db()
set_setting('anthropic_api_key', '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')
print('API key saved to local DB.')
