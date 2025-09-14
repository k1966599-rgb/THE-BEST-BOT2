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
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.txt'):
                    key = filename.replace('_template.txt', '')
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
        all_keys = set(re.findall(r'\{(\w+)\}', template))
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
        """Formats levels into a dictionary by matching on keywords, making it more robust."""
        level_data = {}

        trend_name_map = {'1d': 'طويل المدى', '4h': 'متوسط المدى'}
        trend_name = trend_name_map.get(tf, 'قصير المدى')

        # The keywords to search for in the level names.
        # This is more robust than exact matching.
        level_keyword_map = {
            f'support_trend_{tf}': (["اتجاه", trend_name], supports),
            f'support_channel_{tf}': (["قناة"], supports),
            f'fib_support_0618_{tf}': (["Fibonacci", "0.618"], supports),
            f'fib_support_05_{tf}': (["Fibonacci", "0.5"], supports),
            f'demand_zone_{tf}': (["طلب"], supports),
            f'previous_support_{tf}': (["سابق"], supports),

            f'main_resistance_{tf}': (["مقاومة رئيسية"], resistances),
            f'supply_zone_{tf}': (["عرض"], resistances),
            f'fib_resistance_1_{tf}': (["Fibonacci", "1.0"], resistances),
            f'fib_resistance_1172_{tf}': (["Fibonacci", "1.172"], resistances),
            f'fib_resistance_1618_{tf}': (["Fibonacci", "1.618"], resistances),
            f'pattern_target_{tf}': (["pattern target"], resistances),
        }

        # Iterate through the map and find the first level that contains all keywords
        for key, (keywords, levels) in level_keyword_map.items():
            found_level = "N/A"
            for level in levels:
                # Check if all keywords are present in the level name (case-insensitive)
                if all(keyword.lower() in level.name.lower() for keyword in keywords):
                    found_level = f"${level.value:,.2f}"
                    break
            level_data[key] = found_level

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
