"""Configuration constants and weights for AI Timetable Scheduler.

Defines the penalty weights for soft constraints, the big-M weight for hard violations,
and default algorithmic budgets for systematic and local search solvers.
"""

# Hard constraint penalty weight (any hard violation must overpower all soft penalties combined)
HARD_W = 1000

# Soft constraint weights
# S1: Free periods (gaps) inside a class's day
# S2: Repeating same theory subject in a single day for a class
# S4: Sessions placed in periods preferred to be avoided by teachers
# S5: Back-to-back runs for a teacher exceeding 2 consecutive periods
W = {
    'S1': 2,
    'S2': 3,
    'S4': 1,
    'S5': 2,
}

# Algorithmic search budgets and hyperparameters
DEFAULT_NODE_LIMIT = 500_000
DEFAULT_TIME_LIMIT = 60  # seconds

# Min-Conflicts defaults
DEFAULT_MAX_ITERS = 20_000
DEFAULT_P_WALK = 0.05
DEFAULT_RESTART_AFTER = 2000
DEFAULT_MAX_RESTARTS = 5

# Simulated Annealing defaults
DEFAULT_SA_ALPHA = 0.95
DEFAULT_SA_T_MIN = 0.05
DEFAULT_SA_P0 = 0.8
