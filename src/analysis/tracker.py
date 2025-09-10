import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import uuid

# Assuming models.py is in the same directory
from .models import AnalysisReport, TimeframeAnalysis, TechnicalPattern, Support, Resistance, ExecutiveSummary, ConfirmedTrade

# Define the path for the tracking file
TRACKING_FILE = Path(__file__).parent.parent.parent / 'tracked_analyses.json'

class AnalysisEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle dataclasses and datetime objects."""
    def default(self, o):
        if isinstance(o, (datetime)):
            return o.isoformat()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return super().default(o)

def decode_hook(d: Dict[str, Any]) -> Any:
    """Custom hook to decode the AnalysisReport object."""
    if 'report_id' in d and 'timeframe_analyses' in d:
        # Reconstruct TimeframeAnalysis objects
        timeframes = [
            TimeframeAnalysis(
                timeframe=t['timeframe'],
                current_price=t['current_price'],
                pattern=TechnicalPattern(**t['pattern']),
                supports=[Support(**s) for s in t['supports']],
                resistances=[Resistance(**r) for r in t['resistances']]
            ) for t in d.get('timeframe_analyses', [])
        ]
        # Reconstruct Summary and Trade objects if they exist
        summary = ExecutiveSummary(**d['summary']) if d.get('summary') else None
        trade = ConfirmedTrade(**d['confirmed_trade']) if d.get('confirmed_trade') else None

        # Reconstruct the main report
        return AnalysisReport(
            report_id=d['report_id'],
            pair=d['pair'],
            platform=d['platform'],
            timestamp=datetime.fromisoformat(d['timestamp']) if 'timestamp' in d else datetime.now(),
            analysis_type=d['analysis_type'],
            timeframe_analyses=timeframes,
            summary=summary,
            confirmed_trade=trade,
            is_followed=d.get('is_followed', False)
        )
    return d

class AnalysisTracker:
    """Manages the lifecycle of tracked analyses."""

    def __init__(self, storage_path: Path = TRACKING_FILE):
        self.storage_path = storage_path
        if not self.storage_path.exists():
            self.storage_path.write_text('[]')

    def _read_file(self) -> List[Dict]:
        """Reads the raw data from the tracking file."""
        return json.loads(self.storage_path.read_text(encoding='utf-8'))

    def _write_file(self, data: List[Dict]):
        """Writes data to the tracking file."""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, cls=AnalysisEncoder, indent=4, ensure_ascii=False)

    def follow_analysis(self, report: AnalysisReport) -> str:
        """Adds a new analysis to be tracked."""
        if not report.report_id:
            report.report_id = str(uuid.uuid4())

        report.is_followed = True

        all_reports = self.get_all_analyses()
        # Avoid duplicates
        if any(r.report_id == report.report_id for r in all_reports):
            # If it exists, update it instead of adding
            return self.update_analysis(report)

        all_reports.append(report)
        self._write_file([r.__dict__ for r in all_reports])
        return report.report_id

    def unfollow_analysis(self, report_id: str):
        """Stops tracking an analysis by setting its 'is_followed' flag to False."""
        all_reports = self.get_all_analyses()
        report_found = False
        for report in all_reports:
            if report.report_id == report_id:
                report.is_followed = False
                report_found = True
                break
        if report_found:
            self._write_file([r.__dict__ for r in all_reports])

    def get_followed_analyses(self) -> List[AnalysisReport]:
        """Retrieves all analyses that are currently being followed."""
        all_reports = self.get_all_analyses()
        return [r for r in all_reports if r.is_followed]

    def get_all_analyses(self) -> List[AnalysisReport]:
        """Retrieves all analyses from the tracking file."""
        raw_data = self._read_file()
        return [decode_hook(item) for item in raw_data]

    def get_analysis_by_id(self, report_id: str) -> AnalysisReport | None:
        """Finds a single analysis by its ID."""
        all_reports = self.get_all_analyses()
        for report in all_reports:
            if report.report_id == report_id:
                return report
        return None

    def update_analysis(self, updated_report: AnalysisReport) -> str:
        """Updates an existing tracked analysis."""
        all_reports = self.get_all_analyses()
        # Find the index of the report to update
        idx_to_update = -1
        for i, report in enumerate(all_reports):
            if report.report_id == updated_report.report_id:
                idx_to_update = i
                break

        if idx_to_update != -1:
            all_reports[idx_to_update] = updated_report
            self._write_file([r.__dict__ for r in all_reports])
            return updated_report.report_id
        else:
            # If for some reason it's not found, add it as a new one.
            return self.follow_analysis(updated_report)
