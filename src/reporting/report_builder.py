import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    """
    Builds the final, comprehensive, user-specified report in a multi-message format.
    """
    def __init__(self, config: dict):
        self.config = config
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Loads report templates from the templates directory."""
        templates = {}
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.txt'):
                    with open(os.path.join(template_dir, filename), 'r', encoding='utf-8') as f:
                        templates[filename.replace('_template.txt', '')] = f.read()
        except FileNotFoundError:
            pass
        return templates

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Constructs a list of messages to be sent."""
        if not self.templates:
            return [{"type": "error", "content": "لا يوجد قالب تحليل"}]

        messages = []

        # Message 1: Header
        messages.append({"type": "header", "content": self._format_header(general_info)})

        # Timeframe messages
        timeframe_emojis = {'1D': '📅', '4H': '🕓', '1H': '🕐', '30m': '🕒', '15m': '🕒', '5m': '🕔', '3m': '🕔'}
        sorted_results = sorted(ranked_results, key=lambda x: (
            {'1D': 0, '4H': 1, '1H': 2, '30M': 3, '15M': 4, '5M': 5, '3M': 6}.get(x.get('timeframe', '').upper(), 99)
        ))

        for result in sorted_results:
            emoji = timeframe_emojis.get(result.get('timeframe', 'N/A').upper(), '⚙️')
            messages.append({
                "type": "timeframe",
                "content": self._format_timeframe_section(result, emoji)
            })

        # Summary message
        summary_content, primary_trade_setup = self._format_summary(sorted_results)
        messages.append({
            "type": "final_summary",
            "content": summary_content,
            "keyboard": "follow_ignore" if primary_trade_setup else None,
            "trade_setup": primary_trade_setup
        })

        return messages

    def _format_header(self, general_info: Dict) -> str:
        """Formats the header message."""
        template = self.templates.get('header', '')
        return template.format(
            symbol=general_info.get('symbol', 'N/A').replace('-', '/'),
            exchange="OKX Exchange",
            date_time=datetime.now().strftime('%Y-%m-%d | %H:%M:%S'),
            current_price=f"${general_info.get('current_price', 0):,.0f}",
            analysis_type=general_info.get('analysis_type', 'تحليل شامل'),
            timeframes=' – '.join(general_info.get('timeframes', []))
        )

    def _format_timeframe_section(self, result: Dict, emoji: str) -> str:
        """Formats a single timeframe section."""
        template = self.templates.get('timeframe_section', '')
        analysis = result.get('raw_analysis', {})
        pattern: Optional[Pattern] = (analysis.get('patterns') or [None])[0]

        pattern_details = self._format_pattern_details(pattern, result.get('timeframe')) if pattern else ""

        supports = "\n".join([self._format_level(level) for level in analysis.get('supports', [])])
        resistances = "\n".join([self._format_level(level) for level in analysis.get('resistances', [])])

        return template.format(
            emoji=emoji,
            timeframe=result.get('timeframe', 'N/A'),
            symbol=result.get('symbol', 'N/A').replace('-', '/'),
            pattern_details=pattern_details,
            supports=supports,
            resistances=resistances
        )

    def _format_pattern_details(self, pattern: Pattern, timeframe: str) -> str:
        """Formats the pattern details for a timeframe section."""
        p_status_map = {"Forming": "قيد التكوين", "Active": "مفعل", "Failed": "فشل", "Completed": "مكتمل"}
        timeframe_full_name_map = {'1H': 'ساعة', '4H': '4 ساعات', '1D': 'يومية', '30m': '30 دقيقة', '15m': '15 دقيقة', '5m': '5 دقائق', '3m': '3 دقائق'}

        return (
            f"النموذج الفني: {pattern.name} ({p_status_map.get(pattern.status, pattern.status)})\n"
            f"شروط التفعيل: اختراق المقاومة ${getattr(pattern, 'activation_level', 0):,.0f} مع ثبات شمعة {timeframe_full_name_map.get(timeframe, timeframe)} فوقها\n"
            f"شروط الإلغاء: كسر الدعم ${getattr(pattern, 'invalidation_level', 0):,.0f} مع إغلاق شمعة {timeframe_full_name_map.get(timeframe, timeframe)} تحته"
        )

    def _format_level(self, level: Level) -> str:
        """Formats a single support or resistance level."""
        quality_label = f"({level.quality})" if level.quality else ""
        return f"- {level.name}: ${level.value:,.0f} {quality_label}"

    def _format_summary(self, ranked_results: List[Dict]) -> (str, Optional[TradeSetup]):
        """Formats the summary message."""
        template = self.templates.get('summary', '')

        patterns_summary = self._format_patterns_summary(ranked_results)
        resistance_points, support_points = self._get_critical_points(ranked_results)

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        trade_setup_obj = primary_rec.get('trade_setup') if primary_rec else None
        trade_setup_str = self._format_trade_setup(trade_setup_obj) if trade_setup_obj else "لا توجد صفقة مقترحة حالياً."

        return template.format(
            patterns_summary=patterns_summary,
            resistance_points=resistance_points,
            support_points=support_points,
            trade_setup=trade_setup_str
        ), trade_setup_obj

    def _format_patterns_summary(self, ranked_results: List[Dict]) -> str:
        """Formats the summary of all patterns."""
        p_status_map = {"Forming": "قيد التكوين", "Active": "مفعل", "Failed": "فشل"}
        timeframe_map = {'1H': 'قصير المدى', '4H': 'متوسط المدى', '1D': 'طويل المدى', '30m': 'متوسط المدى', '15m': 'قصير المدى', '5m': 'لحظي', '3m': 'لحظي'}

        lines = []
        for res in ranked_results:
            p: Optional[Pattern] = (res.get('raw_analysis', {}).get('patterns') or [None])[0]
            if p and p.name:
                tf = res.get('timeframe', 'N/A').upper()
                targets_str = ' → '.join([f"${t:,.0f}" for t in [getattr(p, 'target1', None), getattr(p, 'target2', None), getattr(p, 'target3', None)] if t])
                lines.append(f"- {timeframe_map.get(tf, tf)} ({tf}): {p.name} → اختراق ${getattr(p, 'activation_level', 0):,.0f} → أهداف: {targets_str} → حالة النموذج: {p_status_map.get(p.status, p.status)}")
        return "\n".join(lines)

    def _get_critical_points(self, ranked_results: List[Dict]) -> (str, str):
        """Gets the critical resistance and support points."""
        res_points, sup_points = [], []
        for r in ranked_results:
            p: Optional[Pattern] = (r.get('raw_analysis', {}).get('patterns') or [None])[0]
            if p:
                if getattr(p, 'activation_level', 0):
                    res_points.append(f"{r.get('timeframe').upper()} = ${p.activation_level:,.0f}")
                if getattr(p, 'invalidation_level', 0):
                    sup_points.append(f"{r.get('timeframe').upper()} = ${p.invalidation_level:,.0f}")
        return ", ".join(res_points), ", ".join(sup_points)

    def _format_trade_setup(self, setup: TradeSetup) -> str:
        """Formats the trade setup section."""
        return (
            "✅ صفقة مؤكدة:\n"
            f"- سعر الدخول: عند اختراق ${setup.entry_price:,.0f} (فريم {setup.timeframe.upper()}) مع ثبات 3 شموع ساعة فوقه\n"
            f"- الأهداف: {' → '.join([f'${t:,.0f}' for t in [setup.target1, setup.target2] if t])}\n"
            f"- وقف الخسارة: عند كسر ${setup.stop_loss:,.0f}\n"
            f"- ملاحظات: تجنب الدخول على شمعة اختراق وحيدة — انتظر تأكيد الإغلاقات."
        )
