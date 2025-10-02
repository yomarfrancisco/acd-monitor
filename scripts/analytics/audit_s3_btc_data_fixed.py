#!/usr/bin/env python3
"""
Fixed S3 Audit for Real BTC-USD Data Availability
Correctly traverses nested directory structure to find all parquet files.
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

class FixedS3BTCDataAuditor:
    """Fixed audit for real BTC-USD data availability in S3."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = 'acd-monitor-snapshots'
        self.btc_prefix = 'snapshots/BTC-USD/'
        self.venues = ['binance', 'coinbase', 'kraken', 'okx', 'bybit']
        
    def audit_data_availability(self):
        """Audit real BTC-USD data availability in S3 with correct traversal."""
        print("🔍 Fixed S3 Audit - Real BTC-USD Data Availability")
        print("=" * 60)
        
        # List all BTC-USD objects recursively
        print("📥 Listing all BTC-USD objects recursively...")
        all_objects = self._list_all_btc_objects()
        
        if not all_objects:
            print("❌ No BTC-USD objects found in S3")
            return self._generate_empty_report()
        
        print(f"📊 Found {len(all_objects)} BTC-USD objects")
        
        # Analyze by date and time window
        print("\n🔍 Analyzing by date and time window...")
        analysis = self._analyze_objects_by_structure(all_objects)
        
        # Generate comprehensive report
        report = self._generate_fixed_report(analysis)
        
        # Save report
        self._save_fixed_report(report)
        
        print(f"\n✅ Fixed audit completed")
        print(f"📁 Report saved to analysis/wave2/btc_usd_s3_audit/")
        
        return report
    
    def _list_all_btc_objects(self):
        """List all BTC-USD objects recursively."""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.btc_prefix):
                if 'Contents' in page:
                    objects.extend(page['Contents'])
        except Exception as e:
            print(f"❌ Error listing objects: {e}")
            return []
        
        return objects
    
    def _analyze_objects_by_structure(self, objects):
        """Analyze objects by their directory structure."""
        analysis = {
            'total_objects': len(objects),
            'parquet_files': [],
            'by_date': {},
            'by_venue': {venue: [] for venue in self.venues},
            'time_windows': set(),
            'dates': set()
        }
        
        for obj in objects:
            key = obj['Key']
            
            # Parse the key structure: snapshots/BTC-USD/{date}/{time-window}/ticks/{venue}/part-0000.parquet
            parts = key.split('/')
            if len(parts) >= 6 and parts[0] == 'snapshots' and parts[1] == 'BTC-USD':
                date = parts[2]
                time_window = parts[3]
                venue = parts[5] if len(parts) > 5 else None
                
                analysis['dates'].add(date)
                analysis['time_windows'].add(time_window)
                
                # Track parquet files
                if key.endswith('.parquet'):
                    parquet_info = {
                        'key': key,
                        'date': date,
                        'time_window': time_window,
                        'venue': venue,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    }
                    analysis['parquet_files'].append(parquet_info)
                    
                    # Group by date
                    if date not in analysis['by_date']:
                        analysis['by_date'][date] = {
                            'parquet_files': [],
                            'venues': set(),
                            'time_windows': set(),
                            'total_size': 0
                        }
                    
                    analysis['by_date'][date]['parquet_files'].append(parquet_info)
                    analysis['by_date'][date]['venues'].add(venue)
                    analysis['by_date'][date]['time_windows'].add(time_window)
                    analysis['by_date'][date]['total_size'] += obj['Size']
                    
                    # Group by venue
                    if venue in analysis['by_venue']:
                        analysis['by_venue'][venue].append(parquet_info)
        
        return analysis
    
    def _generate_fixed_report(self, analysis):
        """Generate comprehensive fixed audit report."""
        print("\n📋 Generating Fixed Audit Report...")
        
        # Calculate summary statistics
        total_parquet_files = len(analysis['parquet_files'])
        total_dates = len(analysis['dates'])
        total_time_windows = len(analysis['time_windows'])
        
        # Venue coverage
        venue_coverage = {}
        for venue in self.venues:
            venue_files = analysis['by_venue'][venue]
            venue_coverage[venue] = {
                'files_count': len(venue_files),
                'total_size': sum(f['size'] for f in venue_files),
                'dates_present': len(set(f['date'] for f in venue_files))
            }
        
        # Date analysis
        date_analysis = {}
        for date, data in analysis['by_date'].items():
            date_analysis[date] = {
                'parquet_files': len(data['parquet_files']),
                'venues_present': len(data['venues']),
                'time_windows': len(data['time_windows']),
                'total_size': data['total_size'],
                'venues': list(data['venues']),
                'time_windows': list(data['time_windows'])
            }
        
        # Calculate date range
        dates_sorted = sorted(analysis['dates'])
        earliest_date = dates_sorted[0] if dates_sorted else None
        latest_date = dates_sorted[-1] if dates_sorted else None
        
        report = {
            'audit_date': datetime.now().isoformat(),
            'bucket': self.bucket_name,
            'prefix': self.btc_prefix,
            'summary': {
                'total_objects': analysis['total_objects'],
                'parquet_files': total_parquet_files,
                'distinct_dates': total_dates,
                'distinct_time_windows': total_time_windows,
                'earliest_date': earliest_date,
                'latest_date': latest_date,
                'total_size_bytes': sum(f['size'] for f in analysis['parquet_files'])
            },
            'venue_coverage': venue_coverage,
            'date_analysis': date_analysis,
            'time_windows': list(analysis['time_windows']),
            'dates': list(analysis['dates']),
            'recommendations': self._generate_fixed_recommendations(analysis, total_dates)
        }
        
        return report
    
    def _generate_fixed_recommendations(self, analysis, distinct_days):
        """Generate recommendations based on fixed audit findings."""
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
        venue_counts = {venue: len(analysis['by_venue'][venue]) for venue in self.venues}
        good_venues = [v for v, count in venue_counts.items() if count > 0]
        
        if len(good_venues) >= 3:
            recommendations.append("✅ Good venue coverage for analysis")
        elif len(good_venues) >= 1:
            recommendations.append("⚠️ Limited venue coverage - may affect analysis quality")
        else:
            recommendations.append("❌ No venue data found")
        
        return recommendations
    
    def _generate_empty_report(self):
        """Generate report when no data is found."""
        return {
            'audit_date': datetime.now().isoformat(),
            'bucket': self.bucket_name,
            'prefix': self.btc_prefix,
            'summary': {
                'total_objects': 0,
                'parquet_files': 0,
                'distinct_dates': 0,
                'distinct_time_windows': 0,
                'earliest_date': None,
                'latest_date': None,
                'total_size_bytes': 0
            },
            'venue_coverage': {venue: {'files_count': 0, 'total_size': 0, 'dates_present': 0} for venue in self.venues},
            'date_analysis': {},
            'time_windows': [],
            'dates': [],
            'recommendations': ["❌ No BTC-USD data found in S3 - cannot proceed with extended analysis"]
        }
    
    def _save_fixed_report(self, report):
        """Save fixed audit report to files."""
        os.makedirs('analysis/wave2/btc_usd_s3_audit', exist_ok=True)
        
        # Save JSON report
        with open('analysis/wave2/btc_usd_s3_audit/s3_audit_fixed.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save human-readable summary
        with open('analysis/wave2/btc_usd_s3_audit/S3_AUDIT_FIXED_SUMMARY.md', 'w') as f:
            f.write(f"# Fixed S3 BTC-USD Data Availability Audit\n\n")
            f.write(f"**Audit Date**: {report['audit_date']}\n")
            f.write(f"**S3 Bucket**: {report['bucket']}\n")
            f.write(f"**Prefix**: {report['prefix']}\n\n")
            
            f.write("## Summary\n\n")
            summary = report['summary']
            f.write(f"- **Total Objects**: {summary['total_objects']}\n")
            f.write(f"- **Parquet Files**: {summary['parquet_files']}\n")
            f.write(f"- **Distinct Dates**: {summary['distinct_dates']}\n")
            f.write(f"- **Distinct Time Windows**: {summary['distinct_time_windows']}\n")
            f.write(f"- **Earliest Date**: {summary['earliest_date']}\n")
            f.write(f"- **Latest Date**: {summary['latest_date']}\n")
            f.write(f"- **Total Size**: {summary['total_size_bytes']:,} bytes\n\n")
            
            f.write("## Venue Coverage\n\n")
            for venue, data in report['venue_coverage'].items():
                f.write(f"- **{venue}**: {data['files_count']} files, {data['total_size']:,} bytes, {data['dates_present']} dates\n")
            
            f.write("\n## Date Analysis\n\n")
            for date, data in report['date_analysis'].items():
                f.write(f"### {date}\n")
                f.write(f"- **Parquet Files**: {data['parquet_files']}\n")
                f.write(f"- **Venues Present**: {data['venues_present']} ({', '.join(data['venues'])})\n")
                f.write(f"- **Time Windows**: {data['time_windows']}\n")
                f.write(f"- **Total Size**: {data['total_size']:,} bytes\n\n")
            
            f.write("## Recommendations\n\n")
            for rec in report['recommendations']:
                f.write(f"- {rec}\n")
            
            f.write("\n## Next Steps\n\n")
            if summary['distinct_dates'] >= 2:
                f.write("✅ **Proceed with real data alignment**\n")
                f.write("- Assemble multi-day panel from real S3 data\n")
                f.write("- Run extended Wave-2 analysis on authentic data\n")
            else:
                f.write("⚠️ **Insufficient data for extended analysis**\n")
                f.write("- Extend capture period to collect more data\n")
                f.write("- Consider alternative analysis approaches\n")

if __name__ == "__main__":
    auditor = FixedS3BTCDataAuditor()
    auditor.audit_data_availability()
