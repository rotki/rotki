#!/usr/bin/env python
"""Generate a visual representation of the migration progress"""
import json
from datetime import datetime
from pathlib import Path

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Import the analysis functions from the progress script
from check_async_migration_progress import analyze_module, check_endpoint_migration


def generate_text_report():
    """Generate a text-based visual report"""
    project_root = Path(__file__).parent.parent
    
    # Modules to analyze
    modules = {
        'API': project_root / 'rotkehlchen' / 'api',
        'Tasks': project_root / 'rotkehlchen' / 'tasks',
        'Chain': project_root / 'rotkehlchen' / 'chain',
        'Exchanges': project_root / 'rotkehlchen' / 'exchanges',
        'Database': project_root / 'rotkehlchen' / 'db',
        'Core': project_root / 'rotkehlchen',
    }
    
    print("\n" + "=" * 80)
    print(f"ROTKI ASYNC MIGRATION DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    # Module overview as ASCII art
    print("\nMODULE MIGRATION STATUS:")
    print("-" * 60)
    print("Module      | Compat Layer | AsyncIO | Direct Gevent |")
    print("-" * 60)
    
    totals = {'compat': 0, 'async': 0, 'direct': 0, 'total': 0}
    
    for module_name, module_path in modules.items():
        if not module_path.exists():
            continue
            
        stats = analyze_module(module_path)
        total = stats['total_files']
        if total == 0:
            continue
            
        totals['compat'] += stats['using_compat']
        totals['async'] += stats['using_asyncio']
        totals['direct'] += stats['gevent_direct']
        totals['total'] += total
        
        # Create bar visualization
        compat_bar = '█' * int(20 * stats['using_compat'] / total) if total else ''
        async_bar = '▓' * int(20 * stats['using_asyncio'] / total) if total else ''
        direct_bar = '░' * int(20 * stats['gevent_direct'] / total) if total else ''
        
        print(f"{module_name:11} | {stats['using_compat']:3d} {compat_bar:20} | "
              f"{stats['using_asyncio']:3d} {async_bar:20} | "
              f"{stats['gevent_direct']:3d} {direct_bar:20} |")
    
    print("-" * 60)
    
    # Overall summary
    print("\nOVERALL PROGRESS:")
    if totals['total'] > 0:
        compat_pct = totals['compat'] / totals['total'] * 100
        async_pct = totals['async'] / totals['total'] * 100
        direct_pct = totals['direct'] / totals['total'] * 100
        
        print(f"  Compat Layer: {totals['compat']:4d}/{totals['total']} ({compat_pct:5.1f}%) " + 
              '█' * int(compat_pct / 2))
        print(f"  AsyncIO:      {totals['async']:4d}/{totals['total']} ({async_pct:5.1f}%) " + 
              '▓' * int(async_pct / 2))
        print(f"  Direct Gevent:{totals['direct']:4d}/{totals['total']} ({direct_pct:5.1f}%) " + 
              '░' * int(direct_pct / 2))
    
    # Endpoint migration
    endpoint_stats = check_endpoint_migration()
    print(f"\nAPI ENDPOINT MIGRATION:")
    print(f"  Flask:   {endpoint_stats['flask_endpoints']} endpoints")
    print(f"  FastAPI: {endpoint_stats['fastapi_endpoints']} endpoints " +
          f"({endpoint_stats['migration_percentage']:.1f}%)")
    
    # Timeline estimation
    print("\nESTIMATED TIMELINE:")
    remaining_files = totals['direct']
    remaining_endpoints = endpoint_stats['flask_endpoints'] - endpoint_stats['fastapi_endpoints']
    
    # Rough estimates
    days_per_file = 0.1  # Assuming 10 files per day
    days_per_endpoint = 0.5  # Assuming 2 endpoints per day
    
    total_days = remaining_files * days_per_file + remaining_endpoints * days_per_endpoint
    
    print(f"  Files to migrate: {remaining_files} (~{remaining_files * days_per_file:.1f} days)")
    print(f"  Endpoints to migrate: {remaining_endpoints} (~{remaining_endpoints * days_per_endpoint:.1f} days)")
    print(f"  Total estimated time: ~{total_days:.0f} days")
    
    # Save JSON report
    report = {
        'timestamp': datetime.now().isoformat(),
        'modules': {},
        'totals': totals,
        'endpoints': endpoint_stats,
        'estimated_days_remaining': total_days,
    }
    
    for module_name, module_path in modules.items():
        if module_path.exists():
            report['modules'][module_name] = analyze_module(module_path)
    
    report_path = project_root / 'migration_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Generate matplotlib chart if available
    if HAS_MATPLOTLIB:
        generate_chart(report)
    else:
        print("\nInstall matplotlib for graphical charts: pip install matplotlib")


def generate_chart(report: dict):
    """Generate a matplotlib chart of the migration progress"""
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Module breakdown pie chart
    modules = report['modules']
    module_names = []
    compat_counts = []
    async_counts = []
    direct_counts = []
    
    for name, stats in modules.items():
        if stats['total_files'] > 0:
            module_names.append(name)
            compat_counts.append(stats['using_compat'])
            async_counts.append(stats['using_asyncio'])
            direct_counts.append(stats['gevent_direct'])
    
    # Stacked bar chart
    x = range(len(module_names))
    width = 0.6
    
    p1 = ax1.bar(x, compat_counts, width, label='Compat Layer', color='#2ecc71')
    p2 = ax1.bar(x, async_counts, width, bottom=compat_counts, label='AsyncIO', color='#3498db')
    p3 = ax1.bar(x, direct_counts, width, 
                 bottom=[i+j for i,j in zip(compat_counts, async_counts)], 
                 label='Direct Gevent', color='#e74c3c')
    
    ax1.set_ylabel('Number of Files')
    ax1.set_title('Migration Status by Module')
    ax1.set_xticks(x)
    ax1.set_xticklabels(module_names, rotation=45)
    ax1.legend()
    
    # Overall progress pie chart
    totals = report['totals']
    sizes = [
        totals['compat'],
        totals['async'],
        totals['direct'],
        totals['total'] - totals['compat'] - totals['async'] - totals['direct']
    ]
    labels = ['Compat Layer', 'AsyncIO', 'Direct Gevent', 'Not Started']
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#95a5a6']
    explode = (0.1, 0.1, 0, 0)  # Explode migrated slices
    
    ax2.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax2.set_title('Overall Migration Progress')
    
    # Add timestamp
    fig.suptitle(f"Rotki Async Migration Progress - {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                 fontsize=16)
    
    plt.tight_layout()
    
    # Save chart
    chart_path = Path(__file__).parent.parent / 'migration_progress.png'
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    print(f"\nChart saved to: {chart_path}")
    
    # Show chart (optional)
    # plt.show()


if __name__ == '__main__':
    generate_text_report()