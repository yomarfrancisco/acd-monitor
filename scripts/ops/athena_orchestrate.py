#!/usr/bin/env python3
"""
Athena Orchestrator for Zero-Copy Analytics
Submits SQL files to Athena and waits for completion.
No data downloads - all processing server-side.
"""

import boto3
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

class AthenaOrchestrator:
    def __init__(self, workgroup: str = 'acd-analytics', dry_run: bool = False):
        self.athena = boto3.client('athena')
        self.workgroup = workgroup
        self.dry_run = dry_run
        
    def submit_query(self, sql_file: str, output_location: str) -> Optional[str]:
        """Submit a SQL file to Athena and return execution ID."""
        if self.dry_run:
            print(f"🔍 DRY RUN: Would submit {sql_file}")
            print(f"   Output: {output_location}")
            return "dry-run-execution-id"
            
        try:
            with open(sql_file, 'r') as f:
                query = f.read()
                
            response = self.athena.start_query_execution(
                QueryString=query,
                WorkGroup=self.workgroup,
                ResultConfiguration={
                    'OutputLocation': output_location
                }
            )
            
            execution_id = response['QueryExecutionId']
            print(f"✅ Submitted {sql_file} -> {execution_id}")
            return execution_id
            
        except Exception as e:
            print(f"❌ Failed to submit {sql_file}: {e}")
            return None
    
    def wait_for_completion(self, execution_id: str, timeout_minutes: int = 30) -> bool:
        """Wait for query completion with timeout."""
        if self.dry_run:
            print(f"🔍 DRY RUN: Would wait for {execution_id}")
            return True
            
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.athena.get_query_execution(QueryExecutionId=execution_id)
                status = response['QueryExecution']['Status']['State']
                
                if status == 'SUCCEEDED':
                    print(f"✅ Query {execution_id} completed successfully")
                    return True
                elif status == 'FAILED':
                    reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                    print(f"❌ Query {execution_id} failed: {reason}")
                    return False
                elif status == 'CANCELLED':
                    print(f"⚠️ Query {execution_id} was cancelled")
                    return False
                else:
                    print(f"⏳ Query {execution_id} status: {status}")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"❌ Error checking query status: {e}")
                return False
                
        print(f"⏰ Query {execution_id} timed out after {timeout_minutes} minutes")
        return False
    
    def get_query_results(self, execution_id: str) -> Optional[Dict]:
        """Get query results and metadata."""
        if self.dry_run:
            return {"execution_id": execution_id, "status": "dry-run"}
            
        try:
            # Get execution details
            execution = self.athena.get_query_execution(QueryExecutionId=execution_id)
            
            # Get results (first 1000 rows)
            results = self.athena.get_query_results(QueryExecutionId=execution_id, MaxResults=1000)
            
            return {
                "execution_id": execution_id,
                "status": execution['QueryExecution']['Status']['State'],
                "data_scanned": execution['QueryExecution']['Statistics'].get('DataScannedInBytes', 0),
                "execution_time": execution['QueryExecution']['Statistics'].get('TotalExecutionTimeInMillis', 0),
                "result_count": len(results.get('ResultSet', {}).get('Rows', [])) - 1  # Subtract header
            }
            
        except Exception as e:
            print(f"❌ Error getting results: {e}")
            return None
    
    def run_analytics_pipeline(self, date: str = '20250929') -> Dict[str, str]:
        """Run the complete analytics pipeline for a given date."""
        results = {}
        
        # Define pipeline steps
        pipeline = [
            {
                'name': 'panel_1s',
                'sql_file': 'scripts/analytics_athena/panel_1s.sql',
                'output_location': f's3://acd-monitor-derived/athena-results/panel_1s_{date}/'
            },
            {
                'name': 'env_flags', 
                'sql_file': 'scripts/analytics_athena/env_flags.sql',
                'output_location': f's3://acd-monitor-derived/athena-results/env_flags_{date}/'
            },
            {
                'name': 'market_structure',
                'sql_file': 'scripts/analytics_athena/market_structure_5s.sql', 
                'output_location': f's3://acd-monitor-derived/athena-results/market_structure_{date}/'
            },
            {
                'name': 'wave3_features',
                'sql_file': 'scripts/analytics_athena/wave3_features.sql',
                'output_location': f's3://acd-monitor-derived/athena-results/wave3_features_{date}/'
            }
        ]
        
        print(f"🚀 Starting analytics pipeline for {date}")
        print(f"🔍 Dry run mode: {self.dry_run}")
        
        for step in pipeline:
            print(f"\n📊 Step: {step['name']}")
            
            # Submit query
            execution_id = self.submit_query(step['sql_file'], step['output_location'])
            if not execution_id:
                print(f"❌ Failed to submit {step['name']}")
                results[step['name']] = 'FAILED'
                continue
                
            # Wait for completion
            if self.wait_for_completion(execution_id):
                # Get results summary
                summary = self.get_query_results(execution_id)
                results[step['name']] = execution_id
                print(f"✅ {step['name']} completed: {summary}")
            else:
                results[step['name']] = 'TIMEOUT'
                print(f"⏰ {step['name']} timed out")
        
        return results

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Athena Analytics Orchestrator')
    parser.add_argument('--date', default='20250929', help='Date to process (YYYYMMDD)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual execution)')
    parser.add_argument('--workgroup', default='acd-analytics', help='Athena workgroup')
    
    args = parser.parse_args()
    
    orchestrator = AthenaOrchestrator(workgroup=args.workgroup, dry_run=args.dry_run)
    results = orchestrator.run_analytics_pipeline(args.date)
    
    print(f"\n📋 Pipeline Results:")
    for step, result in results.items():
        print(f"  {step}: {result}")
    
    # Save results summary
    output_file = f"analysis/infra/athena/pipeline_results_{args.date}.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'date': args.date,
            'dry_run': args.dry_run,
            'workgroup': args.workgroup,
            'results': results,
            'timestamp': time.time()
        }, f, indent=2)
    
    print(f"📄 Results saved to {output_file}")

if __name__ == "__main__":
    main()


