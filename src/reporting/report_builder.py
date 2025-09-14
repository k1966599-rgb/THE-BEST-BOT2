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

    def _load_templates(self) -> Dict[str, str]:
        """Loads report templates from the templates directory."""
        templates = {}
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.txt'):
                    # Key will be 'long_term', 'medium_term', etc.
                    key = filename.replace('_template.txt', '')
                    with open(os.path.join(template_dir, filename), 'r', encoding='utf-8') as f:
                        templates[key] = f.read()
        except FileNotFoundError:
            # Handle case where directory might not exist
            pass
        return templates

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Constructs a list of messages by preparing data and formatting a split template.
        """
        analysis_type = general_info.get('analysis_type')  # e.g., 'long_term'
        template = self.templates.get(analysis_type)

        if not template:
            return [{"type": "error", "content": f"لم يتم العثور على قالب للتحليل من نوع: {analysis_type}"}]

        # Prepare a single dictionary with all data needed for the template
        report_data, primary_trade_setup = self._prepare_report_data(ranked_results, general_info)

        # Split the template into parts for separate messages
        # Split by lines starting with 🕐, 🕓, 📅, or 📌
        parts = re.split(r'(?m)^(?:🕐|🕓|📅|📌)', template)

        header = parts[0].strip()
        timeframe_sections = []
        summary_section = ""

        # Re-add the splitters to the beginning of each part
        delimiters = re.findall(r'(?m)^(?:🕐|🕓|📅|📌)', template)

        i = 0
        for part in parts[1:]:
            if "الملخص التنفيذي" in part:
                summary_section = (delimiters[i] + part).strip()
            else:
                timeframe_sections.append((delimiters[i] + part).strip())
            i += 1

        messages = []
        # Message 1: Header
        messages.append({"type": "header", "content": header.format(**report_data)})

        # Timeframe messages
        for section in timeframe_sections:
            messages.append({
                "type": "timeframe",
                "content": section.format(**report_data)
            })

        # Final message: Summary with keyboard
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

        # Analysis type for header
        analysis_type_map = {
            "long_term": "استثمار طويل المدى (1D – 4H – 1H)",
            "medium_term": "متوسط المدى (30m – 15m)",
            "short_term": "قصير المدى (5m – 3m)",
        }
        data['analysis_type'] = analysis_type_map.get(general_info.get('analysis_type'), "تحليل شامل")

        # Process each timeframe result
        for result in ranked_results:
            tf = result.get('timeframe', '').lower().replace(' ', '')
            analysis = result.get('raw_analysis', {})

            # Format levels (supports and resistances)
            levels = self._format_levels_for_timeframe(analysis.get('supports', []), analysis.get('resistances', []), tf)
            data.update(levels)

            # Format pattern
            pattern: Optional[Pattern] = (analysis.get('patterns') or [None])[0]
            pattern_data = self._format_pattern_for_timeframe(pattern, tf)
            data.update(pattern_data)

            # Placeholder for summaries (can be enhanced later)
            data[f'summary_{tf}'] = self._generate_simple_summary(pattern, analysis, tf)

        # Process trade setup and critical points
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        trade_setup_obj = primary_rec.get('trade_setup') if primary_rec else None

        trade_setup_data = self._format_trade_setup(trade_setup_obj)
        data.update(trade_setup_data)

        critical_points = self._get_critical_points(ranked_results)
        data.update(critical_points)

        # Set default values for any missing keys to avoid errors
        all_keys = re.findall(r'\{(\w+)\}', "".join(self.templates.values()))
        for key in all_keys:
            if key not in data:
                data[key] = "N/A"

        return data, trade_setup_obj

    def _format_levels_for_timeframe(self, supports: List[Level], resistances: List[Level], tf: str) -> Dict[str, str]:
        """Formats levels into a dictionary for a specific timeframe."""
        level_data = {}

        # Mapping from template placeholder to our internal keywords
        level_map = {
            f'support_trend_{tf}': (["trend", "اتجاه"], supports),
            f'support_channel_{tf}': (["channel", "قناة"], supports),
            f'fib_support_0618_{tf}': (["fibonacci", "0.618"], supports),
            f'fib_support_05_{tf}': (["fibonacci", "0.5"], supports),
            f'demand_zone_{tf}': (["volume", "طلب"], supports),
            f'previous_support_{tf}': (["previous", "historical", "عام"], supports),
            f'main_resistance_{tf}': (["poc", "رئيسية"], resistances),
            f'pattern_target_{tf}': (["target"], resistances),
            f'fib_resistance_1_{tf}': (["fibonacci", "1.0"], resistances),
            f'fib_resistance_1172_{tf}': (["fibonacci", "1.172"], resistances),
            f'fib_resistance_1618_{tf}': (["fibonacci", "1.618"], resistances),
            f'supply_zone_{tf}': (["volume", "عرض"], resistances),
        }

        for key, (keywords, levels) in level_map.items():
            found_level = "N/A"
            for level in levels:
                if any(keyword in level.name.lower() for keyword in keywords):
                    found_level = f"${level.value:,.2f}"
                    break
            level_data[key] = found_level

        return level_data

    def _format_pattern_for_timeframe(self, pattern: Optional[Pattern], tf: str) -> Dict[str, str]:
        """Formats pattern details into a dictionary."""
        if not pattern or not pattern.name:
            return {f'pattern_{tf}': 'لا يوجد', f'activation_{tf}': 'N/A', f'invalidation_{tf}': 'N/A'}

        p_status_map = {"Forming": "قيد التكوين", "Active": "مفعل", "Failed": "فشل", "Completed": "مكتمل"}

        return {
            f'pattern_{tf}': f"{pattern.name} ({p_status_map.get(pattern.status, pattern.status)})",
            f'activation_{tf}': f"اختراق ${getattr(pattern, 'activation_level', 0):,.2f}",
            f'invalidation_{tf}': f"كسر ${getattr(pattern, 'invalidation_level', 0):,.2f}"
        }

    def _generate_simple_summary(self, pattern: Optional[Pattern], analysis: Dict, tf: str) -> str:
        """Generates a one-line summary for a timeframe."""
        if pattern and pattern.name:
            return f"يوجد نموذج {pattern.name} قيد التكوين."

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
