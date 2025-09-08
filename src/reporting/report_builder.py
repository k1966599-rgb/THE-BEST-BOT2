from typing import List, Dict, Any
from datetime import datetime

class ReportBuilder:
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> str:
        header = self._format_header(general_info)

        timeframe_sections = []
        for i, result in enumerate(ranked_results):
            priority = f"الأولوية {i+1}"
            timeframe_sections.append(self._format_timeframe_section(result, priority))

        summary = self._format_summary(ranked_results)

        final_report = f"{header}\n\n" + "\n\n".join(timeframe_sections) + f"\n\n{summary}"
        return final_report

    def _format_header(self, general_info: Dict) -> str:
        return f"""💎 تحليل فني شامل - {general_info.get('symbol')} 💎
معلومات عامة

المنصة: OKX Exchange
التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}
السعر الحالي: ${general_info.get('current_price', 0):,.2f}
نوع التحليل: {general_info.get('analysis_type', 'تحليل شامل')}"""

    def _format_timeframe_section(self, result: Dict, priority: str) -> str:
        timeframe = result.get('timeframe', 'N/A')
        recommendation = result.get('recommendation', {})
        analysis = recommendation.get('raw_analysis', {})

        sr_data = analysis.get('SupportResistanceAnalysis', {})
        pattern_data = analysis.get('ClassicPatterns', {}).get('found_patterns', [])

        section = f"فريم {timeframe} - {priority}\n"
        section += f"السعر الحالي\n${recommendation.get('current_price', 0):,.2f}\n\n"
        section += self._format_sr_section(sr_data)
        if pattern_data:
            section += self._format_pattern_section(pattern_data[0])

        return section

    def _format_sr_section(self, sr_data: Dict) -> str:
        demand_zones = sr_data.get('all_demand_zones', [])
        supply_zones = sr_data.get('all_supply_zones', [])

        text = "الدعوم والمقاومات ومناطق الطلب والعرض\n\n"
        text += "مناطق الطلب:\n"
        if demand_zones:
            for zone in demand_zones[:3]: # Show top 3
                text += f"- {zone.get('strength_text', 'متوسطة')}: ${zone.get('start', 0):,.2f} – ${zone.get('end', 0):,.2f}\n"
        else:
            text += "- لا توجد مناطق طلب واضحة.\n"

        text += "\nمناطق العرض:\n"
        if supply_zones:
             for zone in supply_zones[:3]:
                text += f"- {zone.get('strength_text', 'متوسطة')}: ${zone.get('start', 0):,.2f} – ${zone.get('end', 0):,.2f}\n"
        else:
            text += "- لا توجد مناطق عرض واضحة.\n"

        return text

    def _format_pattern_section(self, pattern: Dict) -> str:
        text = "\nالنموذج الفني\n\n"
        text += f"{pattern.get('name')}\n"
        text += f"هدف النموذج: ${pattern.get('price_target', 0):,.2f}\n"
        text += f"وقف خسارة: ${pattern.get('stop_loss', 0):,.2f}\n"
        text += f"تفعيل النموذج: عند اختراق المقاومة ${pattern.get('activation_level', 0):,.2f}\n"
        text += f"إلغاء النموذج: عند كسر الدعم ${pattern.get('invalidation_level', 0):,.2f}\n"
        return text

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "--- الملخص التنفيذي ---\nلا توجد توصيات."

        primary_rec = ranked_results[0].get('recommendation', {})
        primary_pattern = primary_rec.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]

        entry = primary_pattern.get('activation_level', 0)
        stop_loss = primary_pattern.get('stop_loss', 0)
        target1 = primary_pattern.get('price_target', 0)

        text = "--- الملخص التنفيذي والشامل ---\n\n"
        text += f"أقوى فريم للاختراق قصير المدى: فريم {ranked_results[0].get('timeframe')}\n\n"
        text += "التوصية النهائية بعد دمج تحليل الفريمات:\n"
        text += f"دخول: عند اختراق المقاومة ${entry:,.2f}\n"
        text += f"الأهداف: ${target1:,.2f}\n"
        text += f"وقف الخسارة: عند كسر الدعم ${stop_loss:,.2f}\n"

        return text
