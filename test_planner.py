import sys
from src.agents.general_agent.planner import PlanningAgent
import json

planner = PlanningAgent()
try:
    goal = "Was kosten Bananen bei Migros?"
    state = {'url': 'None (Browser not started yet)', 'last_action_result': 'None'}
    plan = planner.plan_next_step(goal, state)
    print("PLAN SUCCESS:")
    print(json.dumps(plan, indent=2))
except Exception as e:
    print(f"PLAN FAILED: {e}")
