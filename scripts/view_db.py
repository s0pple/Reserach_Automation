import sys
import os

# Add the project root to sys.path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.modules.db.database import get_session, ResearchRun, Opportunity

def view_latest_runs(limit=5):
    try:
        session = get_session()
        runs = session.query(ResearchRun).order_by(ResearchRun.date_run.desc()).limit(limit).all()
        
        if not runs:
            print("No research runs found in the database.")
            return

        print(f"\n{'ID':<3} | {'Domain':<30} | {'Date':<20} | {'Score':<6}")
        print("-" * 65)
        
        for run in runs:
            print(f"{run.id:<3} | {run.domain:<30} | {run.date_run.strftime('%Y-%m-%d %H:%M'):<20} | {run.top_opportunity_score:<6.2f}")
            
            # Show opportunities for each run
            opps = session.query(Opportunity).filter(Opportunity.run_id == run.id).all()
            for opp in opps:
                print(f"  └─ [Score: {opp.score:.2f}] {opp.title}")
        
        session.close()
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    view_latest_runs()
