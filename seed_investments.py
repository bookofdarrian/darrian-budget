import sys
sys.path.insert(0, '.')
from utils.db import init_db, save_investment_context

init_db()

save_investment_context({
    'bal_401k':         14191.77,
    'contrib_401k_ytd': 0.0,
    'match_401k_ytd':   0.0,
    'bal_roth':         9449.28,
    'contrib_roth_ytd': 0.0,
    'bal_hsa':          2339.29,   # Health Savings Account (lower balance)
    'contrib_hsa_ytd':  0.0,
    'bal_brokerage':    5096.79,   # Cash Management Individual (high yield / spend-save)
    'notes':            'Fidelity accounts: VISA 401K Plan ($14,191.77), Roth IRA ($9,449.28), Health Savings Account ($2,339.29), Cash Management Individual / High Yield ($5,096.79). Also: Long-Term ($0.25) and Short-Term ($0.59) investment accounts.',
})
print('Seeded Fidelity balances successfully.')
