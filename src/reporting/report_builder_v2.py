from typing import List, Dict, Any
from datetime import datetime

class ReportBuilderV2:
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
        symbol = general_info.get('symbol', 'N/A')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')

        # Extract timeframes for the title
        timeframes = general_info.get('timeframes', [])
        timeframe_str = " - ".join(tf.upper() for tf in timeframes) if timeframes else ""

        return f"""💎 تحليل فني شامل - {symbol} 💎
معلومات عامة

المنصة: OKX Exchange
التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}
السعر الحالي: ${current_price:,.2f}
نوع التحليل: {analysis_type} ({timeframe_str})"""

    def _format_timeframe_section(self, result: Dict, priority: str) -> str:
        timeframe = result.get('timeframe', 'N/A')
        analysis = result.get('raw_analysis', {})
        current_price = result.get('current_price', 0)

        section = f"فريم {timeframe} - {priority}\n"
        section += f"السعر الحالي\n${current_price:,.2f}\n\n"

        section += self._format_trends_and_channels(analysis.get('TrendAnalysis', {}), analysis.get('PriceChannels', {}))
        section += self._format_sr_section(analysis.get('SupportResistanceAnalysis', {}), current_price)
        section += self._format_pattern_section(analysis.get('ClassicPatterns', {}))
        section += self._format_scenarios_section(analysis, current_price)

        return section

    def _format_trends_and_channels(self, trend_data: Dict, channel_data: Dict) -> str:
        if not trend_data and not channel_data:
            return ""

        text = "القنوات السعرية والترندات\n\n"

        trend_direction = trend_data.get('trend_direction', 'غير محدد')
        if trend_direction == 'Uptrend':
            text += f"ترند صاعد\n"
        elif trend_direction == 'Downtrend':
            text += f"ترند هابط\n"
        else:
            text += f"ترند عرضي\n"

        channel_trend = channel_data.get('channel_trend', 'عرضي')
        upper_band = channel_data.get('upper_band', 0)
        if channel_trend != 'عرضي':
            text += f"مقاومة القناة: ${upper_band:,.2f}\n"

        text += "\n"
        return text

    def _format_sr_section(self, sr_data: Dict, current_price: float) -> str:
        if not sr_data:
            return ""

        text = "الدعوم والمقاومات ومناطق الطلب والعرض\n\n"

        # Demand Zones
        text += "مناطق الطلب:\n"
        demand_zones = sr_data.get('all_demand_zones', [])
        if demand_zones:
            for zone in demand_zones[:3]:
                text += f"- {zone.get('strength_text', 'متوسطة')}: ${zone.get('start', 0):,.2f} – ${zone.get('end', 0):,.2f}\n"
        else:
            text += "- لا توجد مناطق طلب واضحة.\n"

        # Supply Zones
        text += "\nمناطق العرض:\n"
        supply_zones = sr_data.get('all_supply_zones', [])
        if supply_zones:
             for zone in supply_zones[:3]:
                text += f"- {zone.get('strength_text', 'متوسطة')}: ${zone.get('start', 0):,.2f} – ${zone.get('end', 0):,.2f}\n"
        else:
            text += "- لا توجد مناطق عرض واضحة.\n"

        # Supports and Resistances
        supports = sr_data.get('supports', [])
        if supports:
            text += f"\nالدعوم: {', '.join([f'${s:,.2f}' for s in supports[:3]])}\n"

        resistances = sr_data.get('resistances', [])
        if resistances:
            text += f"المقاومات: {', '.join([f'${r:,.2f}' for r in resistances[:3]])}\n"

        text += "\n"
        return text

    def _format_pattern_section(self, pattern_data: Dict) -> str:
        if not pattern_data or not pattern_data.get('found_patterns'):
            return ""

        pattern = pattern_data['found_patterns'][0]
        text = "النموذج الفني\n\n"
        text += f"{pattern.get('name')} ({pattern.get('status', 'مكتمل')})\n"
        text += f"هدف النموذج: ${pattern.get('price_target', 0):,.2f}\n"
        text += f"وقف خسارة: ${pattern.get('stop_loss', 0):,.2f}\n"
        text += f"تفعيل النموذج: عند اختراق المقاومة ${pattern.get('activation_level', 0):,.2f}\n"
        text += f"إلغاء النموذج: عند كسر الدعم ${pattern.get('invalidation_level', 0):,.2f}\n\n"
        return text

    def _format_scenarios_section(self, analysis_results: Dict, current_price: float) -> str:
        # This is a simplified version. A more advanced version could use ML or more complex rules.
        text = "السيناريوهات المحتملة\n\n"

        main_action = "محايد"
        confidence = 50
        pattern = analysis_results.get('ClassicPatterns', {}).get('found_patterns', [{}])[0]

        if 'صاعد' in pattern.get('name', '') or 'قاع' in pattern.get('name', ''):
            main_action = "صاعد"
            confidence = pattern.get('confidence', 70)
        elif 'هابط' in pattern.get('name', '') or 'قمة' in pattern.get('name', ''):
            main_action = "هابط"
            confidence = pattern.get('confidence', 70)

        bull_prob = 0
        bear_prob = 0

        if main_action == "صاعد":
            bull_prob = confidence
            bear_prob = 15
        elif main_action == "هابط":
            bull_prob = 15
            bear_prob = confidence
        else: # Neutral
            bull_prob = 40
            bear_prob = 40

        neutral_prob = 100 - bull_prob - bear_prob

        # Bullish Scenario
        text += f"السيناريو الصاعد ({bull_prob}%)\n"
        target = pattern.get('price_target', current_price * 1.05)
        activation = pattern.get('activation_level', current_price * 1.01)
        text += f"اختراق المقاومة ${activation:,.2f}: الهدف الأول ${target:,.2f}\n\n"

        # Neutral Scenario
        text += f"السيناريو المحايد ({neutral_prob}%)\n"
        support = pattern.get('invalidation_level', current_price * 0.99)
        resistance = pattern.get('activation_level', current_price * 1.01)
        text += f"البقاء داخل النطاق: تداول عرضي بين ${support:,.2f} – ${resistance:,.2f}\n\n"

        # Bearish Scenario
        text += f"السيناريو الهابط ({bear_prob}%)\n"
        stop_loss = pattern.get('stop_loss', current_price * 0.95)
        invalidation = pattern.get('invalidation_level', current_price * 0.99)
        text += f"كسر الدعم ${invalidation:,.2f}: الهدف الأول ${stop_loss:,.2f}\n"

        return text

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "--- الملخص التنفيذي والشامل ---\nلا توجد بيانات كافية لتوليد ملخص."

        text = "--- الملخص التنفيذي والشامل ---\n\n"

        # Identify strongest patterns for different time horizons
        timeframe_map = {
            '1h': 'قصير المدى', '4h': 'متوسط المدى', '1d': 'طويل المدى',
            '1H': 'قصير المدى', '4H': 'متوسط المدى', '1D': 'طويل المدى'
        }

        strongest_patterns = {}
        for res in ranked_results:
            tf = res.get('timeframe')
            horizon = timeframe_map.get(tf, 'غير محدد')
            pattern_data = res.get('raw_analysis', {}).get('ClassicPatterns', {})
            if pattern_data.get('found_patterns'):
                pattern_name = pattern_data['found_patterns'][0]['name']
                if horizon not in strongest_patterns:
                    strongest_patterns[horizon] = f"فريم {tf} ({pattern_name})"

        text += f"أقوى فريم للاختراق قصير المدى: {strongest_patterns.get('قصير المدى', 'N/A')}\n"
        text += f"متوسط المدى: {strongest_patterns.get('متوسط المدى', 'N/A')}\n"
        text += f"طويل المدى: {strongest_patterns.get('طويل المدى', 'N/A')}\n\n"

        # Critical monitoring points
        text += "نقاط المراقبة الحرجة\n"
        critical_resistances = []
        critical_supports = []
        for res in ranked_results:
            tf = res.get('timeframe')
            pattern = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]
            if pattern.get('activation_level'):
                critical_resistances.append(f"{tf} ${pattern['activation_level']:,.2f}")
            if pattern.get('invalidation_level'):
                critical_supports.append(f"{tf} ${pattern['invalidation_level']:,.2f}")

        text += f"اختراق المقاومة: {', '.join(critical_resistances)}\n"
        text += f"كسر الدعم: {', '.join(critical_supports)}\n\n"

        # Final Recommendation based on the primary (highest ranked) result
        primary_rec = ranked_results[0]
        primary_pattern = primary_rec.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]
        primary_timeframe = primary_rec.get('timeframe')

        text += "التوصية النهائية بعد دمج تحليل الفريمات الثلاثة\n"

        entry = primary_pattern.get('activation_level', 0)
        target1 = primary_pattern.get('price_target', 0)
        target2 = target1 * 1.02 if target1 > 0 else 0 # Simplified second target
        stop_loss = primary_pattern.get('stop_loss', 0)

        text += f"دخول: عند اختراق المقاومة ${entry:,.2f} مع تأكيد قوة المؤشرات على فريم {primary_timeframe}\n"
        text += f"الأهداف: ${target1:,.2f} → ${target2:,.2f}\n"
        text += f"وقف الخسارة: عند كسر الدعم ${stop_loss:,.2f} (فريم {primary_timeframe})\n\n"

        # Strategy for other timeframes
        text += "استراتيجية دعم الفريمات:\n"
        for res in ranked_results[1:]: # The rest of the timeframes
             tf = res.get('timeframe')
             pattern = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]
             if pattern.get('activation_level') and pattern.get('price_target'):
                 text += f"متابعة فريم {tf} لاختراق ${pattern['activation_level']:,.2f} للأهداف ${pattern['price_target']:,.2f}\n"

        text += "\nملاحظات: إذا أي فريم يعطي إشارة عكسية قوية (كسر الدعم أو ضعف المؤشرات) → إعادة تقييم الدخول أو ضبط وقف الخسارة\n"

        return text
