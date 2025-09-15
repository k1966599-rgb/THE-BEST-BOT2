import re
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    """
    Builds the final report from a single template, splitting it into multiple messages.
    """
    def __init__(self, config: dict):
        self.config = config
        self.templates = self._load_templates()
        self.analysis_type_map = {
            "long_term": "استثمار طويل المدى",
            "medium_term": "تداول متوسط المدى",
            "short_term": "مضاربة سريعة",
        }
        self.reverse_analysis_type_map = {v: k for k, v in self.analysis_type_map.items()}

    def _load_templates(self) -> Dict[str, str]:
        """Loads report templates from the templates directory."""
        templates = {}
        template_dir = os.path.join(os.path.dirname(__file__), 'new_templates')
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.txt'):
                    key = filename.replace('.txt', '')
                    with open(os.path.join(template_dir, filename), 'r', encoding='utf-8') as f:
                        templates[key] = f.read()
        except FileNotFoundError:
            pass
        return templates

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Constructs a list of messages by preparing data and formatting a split template.
        """
        analysis_type_display = general_info.get('analysis_type')
        # Get the English key ('long_term') from the Arabic display name
        analysis_type_key = self.reverse_analysis_type_map.get(analysis_type_display, 'long_term')
        template = self.templates.get(analysis_type_key)

        if not template:
            return [{"type": "error", "content": f"لم يتم العثور على قالب للتحليل من نوع: {analysis_type_display}"}]

        report_data, primary_trade_setup = self._prepare_report_data(ranked_results, general_info)

        # Use a regex that won't capture the emojis themselves in the split
        parts = re.split(r'(?m)(?=🕐|🕓|📅|📌)', template)

        header = parts[0].strip()
        timeframe_sections = []
        summary_section = ""

        for part in parts[1:]:
            if "الملخص التنفيذي" in part:
                summary_section = part.strip()
            else:
                timeframe_sections.append(part.strip())

        messages = []
        # Ensure all keys have a default value to prevent format errors
        all_keys = set(re.findall(r'\{([\w_]+)\}', template))
        for key in all_keys:
            if key not in report_data:
                report_data[key] = "N/A"

        messages.append({"type": "header", "content": header.format(**report_data)})
        for section in timeframe_sections:
            messages.append({"type": "timeframe", "content": section.format(**report_data)})

        if summary_section:
            messages.append({
                "type": "final_summary",
                "content": summary_section.format(**report_data),
                "keyboard": "follow_ignore" if primary_trade_setup else None,
                "trade_setup": primary_trade_setup
            })

        return messages

    def _prepare_report_data(self, ranked_results: List[Dict], general_info: Dict) -> (Dict[str, Any], Optional[TradeSetup]):
        """
        Prepares a single dictionary with all placeholders for the templates.
        """
        data = {
            'symbol': general_info.get('symbol', 'N/A').replace('-', '/'),
            'exchange': "OKX",
            'date_time': datetime.now().strftime('%Y-%m-%d | %H:%M:%S'),
            'current_price': f"${general_info.get('current_price', 0):,.2f}",
        }

        # The display name is now passed directly from the bot, which gets it from the analysis_type_map
        analysis_type_key = self.reverse_analysis_type_map.get(general_info.get('analysis_type'), 'long_term')
        display_name = self.analysis_type_map.get(analysis_type_key, "تحليل شامل")

        timeframes_str = f"({ ' – '.join(self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {}).get(analysis_type_key, [])) })"
        data['analysis_type'] = f"{display_name} {timeframes_str}"

        for result in ranked_results:
            tf_raw = result.get('timeframe', '')
            tf = tf_raw.lower().replace(' ', '')
            analysis = result.get('raw_analysis', {})

            levels = self._format_levels_for_timeframe(analysis.get('supports', []), analysis.get('resistances', []), tf)
            data.update(levels)

            pattern: Optional[Pattern] = (analysis.get('patterns') or [None])[0]
            pattern_data = self._format_pattern_for_timeframe(pattern, tf)
            data.update(pattern_data)

            data[f'summary_{tf}'] = self._generate_simple_summary(pattern, analysis)

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        trade_setup_obj = primary_rec.get('trade_setup') if primary_rec else None

        trade_setup_data = self._format_trade_setup(trade_setup_obj)
        data.update(trade_setup_data)

        critical_points = self._get_critical_points(ranked_results)
        data.update(critical_points)

        return data, trade_setup_obj

    def _format_levels_for_timeframe(self, supports: List[Level], resistances: List[Level], tf: str) -> Dict[str, str]:
        level_data = {}

        # Initialize all possible placeholders to N/A
        placeholders = [
            'support_channel', 'previous_support_secondary', 'previous_support_critical',
            'historical_bottom', 'confluence_short_trend_support', 'confluence_mid_trend_support',
            'confluence_long_trend_support', 'confluence_main_support',
            'confluence_previous_secondary_support', 'confluence_previous_critical_support',
            'demand_zone', 'fib_support_0_618', 'fib_support_0_5',
            'resistance_channel', 'confluence_short_trend_resistance', 'confluence_main_resistance',
            'confluence_secondary_resistance', 'confluence_pattern_target', 'pattern_target',
            'fib_resistance_1_618'
        ]
        for p in placeholders:
            level_data[f"{p}_{tf}"] = "N/A"

        # Process supports
        for level in supports:
            name = level.name
            value_str = f"${level.value:,.2f}"

            if "دعم القناة السعرية" in name:
                level_data[f'support_channel_{tf}'] = value_str
            elif "دعم عام سابق (ثانوي)" in name:
                level_data[f'previous_support_secondary_{tf}'] = value_str
            elif "دعم عام سابق (حرج)" in name:
                level_data[f'previous_support_critical_{tf}'] = value_str
            elif "قاع تاريخي" in name:
                level_data[f'historical_bottom_{tf}'] = value_str
            elif "منطقة التقاء: دعم الاتجاه قصير المدى" in name:
                level_data[f'confluence_short_trend_support_{tf}'] = value_str
            elif "منطقة التقاء: دعم الاتجاه متوسط المدى" in name:
                level_data[f'confluence_mid_trend_support_{tf}'] = value_str
            elif "منطقة التقاء: دعم الاتجاه طويل المدى" in name:
                level_data[f'confluence_long_trend_support_{tf}'] = value_str
            elif "منطقة التقاء: دعم رئيسي" in name:
                level_data[f'confluence_main_support_{tf}'] = value_str
            elif "منطقة التقاء: دعم عام سابق (ثانوي)" in name:
                level_data[f'confluence_previous_secondary_support_{tf}'] = value_str
            elif "منطقة التقاء: دعم عام سابق (حرج)" in name:
                level_data[f'confluence_previous_critical_support_{tf}'] = value_str
            elif "منطقة طلب عالية" in name:
                level_data[f'demand_zone_{tf}'] = value_str
            elif "0.618" in name:
                level_data[f'fib_support_0_618_{tf}'] = value_str
            elif "0.5" in name:
                level_data[f'fib_support_0_5_{tf}'] = value_str

        # Process resistances
        for level in resistances:
            name = level.name
            value_str = f"${level.value:,.2f}"

            if "مقاومة القناة السعرية" in name:
                level_data[f'resistance_channel_{tf}'] = value_str
            elif "منطقة التقاء: مقاومة الاتجاه قصير المدى" in name:
                level_data[f'confluence_short_trend_resistance_{tf}'] = value_str
            elif "منطقة التقاء: مقاومة رئيسية (حرج)" in name:
                level_data[f'confluence_main_resistance_{tf}'] = value_str
            elif "منطقة التقاء: مقاومة عامة (ثانوي)" in name:
                level_data[f'confluence_secondary_resistance_{tf}'] = value_str
            elif "منطقة التقاء: هدف النموذج" in name:
                level_data[f'confluence_pattern_target_{tf}'] = value_str
            elif "هدف النموذج" in name:
                level_data[f'pattern_target_{tf}'] = value_str
            elif "1.618" in name:
                level_data[f'fib_resistance_1_618_{tf}'] = value_str

        return level_data

    def _format_pattern_for_timeframe(self, pattern: Optional[Pattern], tf: str) -> Dict[str, str]:
        """Formats pattern details into a dictionary."""
        if not pattern or not pattern.name:
            return {f'pattern_{tf}': 'لا يوجد', f'activation_{tf}': 'N/A', f'invalidation_{tf}': 'N/A'}

        p_status_map = {"Forming": "قيد التكوين", "Active": "نشط", "Failed": "فشل", "Completed": "مكتمل"}

        return {
            f'pattern_{tf}': f"{pattern.name} ({p_status_map.get(pattern.status, pattern.status)})",
            f'activation_{tf}': f"اختراق ${getattr(pattern, 'activation_level', 0):,.2f}",
            f'invalidation_{tf}': f"كسر ${getattr(pattern, 'invalidation_level', 0):,.2f}"
        }

    def _generate_simple_summary(self, pattern: Optional[Pattern], analysis: Dict) -> str:
        """Generates a one-line summary for a timeframe."""
        if pattern and pattern.name and pattern.status:
             p_status_map = {"Forming": "قيد التكوين", "Active": "نشط", "Failed": "فشل", "Completed": "مكتمل"}
             return f"يوجد نموذج {pattern.name} {p_status_map.get(pattern.status, pattern.status)}."

        strongest_support = (analysis.get('supports') or [None])[0]
        if strongest_support:
            return f"أقرب دعم هام عند ${strongest_support.value:,.2f}."

        return "لا توجد إشارات فنية واضحة."

    def _get_critical_points(self, ranked_results: List[Dict]) -> Dict[str, str]:
        """Gets the critical resistance and support points for the summary."""
        res_points, sup_points = [], []
        for r in ranked_results:
            p: Optional[Pattern] = (r.get('raw_analysis', {}).get('patterns') or [None])[0]
            if p:
                if getattr(p, 'activation_level', 0):
                    res_points.append(f"{r.get('timeframe').upper()}: ${p.activation_level:,.2f}")
                if getattr(p, 'invalidation_level', 0):
                    sup_points.append(f"{r.get('timeframe').upper()}: ${p.invalidation_level:,.2f}")
        return {
            'resistance_break_levels': ", ".join(res_points) if res_points else "N/A",
            'support_break_levels': ", ".join(sup_points) if sup_points else "N/A"
        }

    def _format_trade_setup(self, setup: Optional[TradeSetup]) -> Dict[str, str]:
        """Formats the trade setup section into a dictionary."""
        if not setup:
            return {'entry_price': 'N/A', 'targets': 'N/A', 'stop_loss': 'N/A', 'trade_notes': 'لا توجد صفقة مقترحة حالياً.'}

        return {
            'entry_price': f"عند اختراق ${setup.entry_price:,.2f}",
            'targets': ' → '.join([f'${t:,.2f}' for t in [setup.target1, setup.target2] if t]),
            'stop_loss': f"عند كسر ${setup.stop_loss:,.2f}",
            'trade_notes': f"تجنب الدخول على شمعة اختراق وحيدة. انتظر تأكيد إغلاق شمعة {setup.timeframe.upper()}."
        }
