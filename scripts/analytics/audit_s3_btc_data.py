#!/usr/bin/env python3
"""
Audit S3 for Real BTC-USD Data Availability
Check actual data availability before extending analysis.
"""

import boto3
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class S3BTCDataAuditor:
    """Audit real BTC-USD data availability in S3."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'acd-monitor-snapshots'
        self.btc_prefix = 'snapshots/BTC-USD/'
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        
    def audit_data_availability(self):
        """Audit real BTC-USD data availability in S3."""
        print("🔍 Auditing Real BTC-USD Data Availability in S3")
        print("=" * 60)
        
        # List all BTC-USD snapshots
        print("📥 Listing BTC-USD snapshots from S3...")
        snapshots = self._list_btc_snapshots()
        
        if not snapshots:
            print("❌ No BTC-USD snapshots found in S3")
            return self._generate_empty_report()
        
        print(f"📊 Found {len(snapshots)} BTC-USD snapshots")
        
        # Analyze each snapshot
        print("\n🔍 Analyzing snapshots...")
        snapshot_analysis = []
        
        for snapshot in snapshots:
            print(f"  📅 Analyzing {snapshot['name']}...")
            analysis = self._analyze_snapshot(snapshot)
            snapshot_analysis.append(analysis)
        
        # Generate comprehensive report
        report = self._generate_report(snapshot_analysis)
        
        # Save report
        self._save_report(report)
        
        print(f"\n✅ Audit completed")
        print(f"📁 Report saved to analysis/wave2/btc_usd_s3_audit/")
        
        return report
    
    def _list_btc_snapshots(self):
        """List all BTC-USD snapshots in S3."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.btc_prefix,
                Delimiter='/'
            )
            
            snapshots = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    snapshot_name = prefix['Prefix'].split('/')[-2]
                    snapshots.append({
                        'name': snapshot_name,
                        'prefix': prefix['Prefix']
                    })
            
            return snapshots
            
        except Exception as e:
            print(f"❌ Error listing snapshots: {e}")
            return []
    
    def _analyze_snapshot(self, snapshot):
        """Analyze a single snapshot for data availability."""
        snapshot_name = snapshot['name']
        prefix = snapshot['prefix']
        
        analysis = {
            'snapshot_name': snapshot_name,
            'timestamp': None,
            'venues_available': [],
            'venue_coverage': {},
            'total_rows': 0,
            'date_range': None,
            'status': 'unknown'
        }
        
        try:
            # Parse timestamp from snapshot name
            if 'T' in snapshot_name:
                timestamp_str = snapshot_name.split('T')[0] + 'T' + snapshot_name.split('T')[1].replace('-', ':')
                analysis['timestamp'] = pd.to_datetime(timestamp_str)
                analysis['date_range'] = {
                    'start': str(analysis['timestamp']),
                    'end': str(analysis['timestamp'] + timedelta(hours=1))
                }
            
            # Check venue data availability
            for venue in self.venues:
                venue_prefix = f"{prefix}{venue}/"
                venue_files = self._list_venue_files(venue_prefix)
                
                if venue_files:
                    analysis['venues_available'].append(venue)
                    analysis['venue_coverage'][venue] = {
                        'files_count': len(venue_files),
                        'has_data': True
                    }
                else:
                    analysis['venue_coverage'][venue] = {
                        'files_count': 0,
                        'has_data': False
                    }
            
            # Estimate total rows (simplified)
            analysis['total_rows'] = len(analysis['venues_available']) * 1000  # Rough estimate
            
            # Determine status
            if len(analysis['venues_available']) >= 3:
                analysis['status'] = 'good'
            elif len(analysis['venues_available']) >= 1:
                analysis['status'] = 'partial'
            else:
                analysis['status'] = 'empty'
                
        except Exception as e:
            analysis['status'] = 'error'
            analysis['error'] = str(e)
        
        return analysis
    
    def _list_venue_files(self, venue_prefix):
        """List files for a specific venue."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=venue_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.parquet'):
                        files.append(obj['Key'])
            
            return files
            
        except Exception as e:
            print(f"    ⚠️ Error listing files for {venue_prefix}: {e}")
            return []
    
    def _generate_report(self, snapshot_analysis):
        """Generate comprehensive audit report."""
        print("\n📋 Generating Audit Report...")
        
        # Calculate summary statistics
        total_snapshots = len(snapshot_analysis)
        good_snapshots = len([s for s in snapshot_analysis if s['status'] == 'good'])
        partial_snapshots = len([s for s in snapshot_analysis if s['status'] == 'partial'])
        empty_snapshots = len([s for s in snapshot_analysis if s['status'] == 'empty'])
        error_snapshots = len([s for s in snapshot_analysis if s['status'] == 'error'])
        
        # Calculate date range
        timestamps = [s['timestamp'] for s in snapshot_analysis if s['timestamp'] is not None]
        if timestamps:
            earliest = min(timestamps)
            latest = max(timestamps)
            distinct_days = len(set([t.date() for t in timestamps if t is not None]))
        else:
            earliest = None
            latest = None
            distinct_days = 0
        
        # Venue coverage analysis
        venue_counts = {}
        for venue in self.venues:
            venue_counts[venue] = len([s for s in snapshot_analysis if venue in s['venues_available']])
        
        report = {
            'audit_date': datetime.now().isoformat(),
            'bucket': self.bucket_name,
            'prefix': self.btc_prefix,
            'summary': {
                'total_snapshots': total_snapshots,
                'good_snapshots': good_snapshots,
                'partial_snapshots': partial_snapshots,
                'empty_snapshots': empty_snapshots,
                'error_snapshots': error_snapshots,
                'distinct_days': distinct_days,
                'earliest_timestamp': str(earliest) if earliest else None,
                'latest_timestamp': str(latest) if latest else None
            },
            'venue_coverage': venue_counts,
            'snapshots': snapshot_analysis,
            'recommendations': self._generate_recommendations(snapshot_analysis, distinct_days)
        }
        
        return report
    
    def _generate_recommendations(self, snapshot_analysis, distinct_days):
        """Generate recommendations based on audit findings."""
        recommendations = []
        
        if distinct_days == 0:
            recommendations.append("❌ No real BTC-USD data found - cannot proceed with extended analysis")
        elif distinct_days == 1:
            recommendations.append("⚠️ Only 1 day of data available - insufficient for multi-day analysis")
            recommendations.append("💡 Consider extending capture period before analysis")
        elif distinct_days >= 2:
            recommendations.append("✅ Sufficient data available for multi-day analysis")
            recommendations.append("💡 Proceed with real data alignment and extended analysis")
        
        # Check venue coverage
        venue_counts = {}
        for venue in self.venues:
            venue_counts[venue] = len([s for s in snapshot_analysis if venue in s['venues_available']])
        
        good_venues = [v for v, count in venue_counts.items() if count >= distinct_days * 0.8]
        if len(good_venues) < 3:
            recommendations.append("⚠️ Limited venue coverage - may affect analysis quality")
        
        return recommendations
    
    def _generate_empty_report(self):
        """Generate report when no data is found."""
        return {
            'audit_date': datetime.now().isoformat(),
            'bucket': self.bucket_name,
            'prefix': self.btc_prefix,
            'summary': {
                'total_snapshots': 0,
                'good_snapshots': 0,
                'partial_snapshots': 0,
                'empty_snapshots': 0,
                'error_snapshots': 0,
                'distinct_days': 0,
                'earliest_timestamp': None,
                'latest_timestamp': None
            },
            'venue_coverage': {venue: 0 for venue in self.venues},
            'snapshots': [],
            'recommendations': ["❌ No BTC-USD data found in S3 - cannot proceed with extended analysis"]
        }
    
    def _save_report(self, report):
        """Save audit report to files."""
        os.makedirs('analysis/wave2/btc_usd_s3_audit', exist_ok=True)
        
        # Save JSON report
        with open('analysis/wave2/btc_usd_s3_audit/s3_audit_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save human-readable summary
        with open('analysis/wave2/btc_usd_s3_audit/S3_AUDIT_SUMMARY.md', 'w') as f:
            f.write(f"# S3 BTC-USD Data Availability Audit\n\n")
            f.write(f"**Audit Date**: {report['audit_date']}\n")
            f.write(f"**S3 Bucket**: {report['bucket']}\n")
            f.write(f"**Prefix**: {report['prefix']}\n\n")
            
            f.write("## Summary\n\n")
            summary = report['summary']
            f.write(f"- **Total Snapshots**: {summary['total_snapshots']}\n")
            f.write(f"- **Good Snapshots**: {summary['good_snapshots']}\n")
            f.write(f"- **Partial Snapshots**: {summary['partial_snapshots']}\n")
            f.write(f"- **Empty Snapshots**: {summary['empty_snapshots']}\n")
            f.write(f"- **Error Snapshots**: {summary['error_snapshots']}\n")
            f.write(f"- **Distinct Days**: {summary['distinct_days']}\n")
            f.write(f"- **Earliest**: {summary['earliest_timestamp']}\n")
            f.write(f"- **Latest**: {summary['latest_timestamp']}\n\n")
            
            f.write("## Venue Coverage\n\n")
            for venue, count in report['venue_coverage'].items():
                f.write(f"- **{venue}**: {count} snapshots\n")
            
            f.write("\n## Recommendations\n\n")
            for rec in report['recommendations']:
                f.write(f"- {rec}\n")
            
            f.write("\n## Next Steps\n\n")
            if summary['distinct_days'] >= 2:
                f.write("✅ **Proceed with real data alignment**\n")
                f.write("- Align multi-day panel from real S3 data\n")
                f.write("- Run extended Wave-2 analysis on authentic data\n")
            else:
                f.write("⚠️ **Insufficient data for extended analysis**\n")
                f.write("- Extend capture period to collect more data\n")
                f.write("- Consider alternative analysis approaches\n")

if __name__ == "__main__":
    auditor = S3BTCDataAuditor()
    auditor.audit_data_availability()
