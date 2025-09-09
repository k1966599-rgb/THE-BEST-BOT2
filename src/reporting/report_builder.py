from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup

class ReportBuilder:
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> Dict[str, Any]:
        header = self._format_header(general_info)

        timeframe_sections = []
        for i, result in enumerate(ranked_results):
            priority = f"الأولوية {i+1}"
            timeframe_sections.append(self._format_timeframe_section(result, priority))

        summary = self._format_summary(ranked_results)
        final_recommendation = self._format_final_recommendation(ranked_results)

        return {
            "header": header,
            "timeframe_sections": timeframe_sections,
            "summary_and_recommendation": f"{summary}\n\n{final_recommendation}"
        }

    def _format_header(self, general_info: Dict) -> str:
        symbol = general_info.get('symbol', 'N/A')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')
        timeframes = general_info.get('timeframes', [])
        timeframe_str = " - ".join(tf.upper() for tf in timeframes) if timeframes else ""

        return f"""💎 تحليل فني شامل - {symbol} 💎

📊 معلومات عامة
🏢 المنصة: OKX Exchange
📅 التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}
💰 السعر الحالي: ${current_price:,.2f}
📈 نوع التحليل: {analysis_type} ({timeframe_str})"""

    def _get_indicator_rating(self, score: float) -> (int, str):
        """Scales a score to a 1-5 rating and selects an emoji."""
        if score > 4:
            return 5, "🚀"
        elif score > 2:
            return 4, "📈"
        elif score > -1:
            return 3, "📊"
        elif score > -3:
            return 2, "📉"
        else:
            return 1, "🔻"

    def _format_timeframe_section(self, result: Dict, priority: str) -> str:
        timeframe = result.get('timeframe', 'N/A')
        analysis = result.get('raw_analysis', {})
        current_price = result.get('current_price', 0)

        sr_data = analysis.get('SupportResistanceAnalysis', {})
        channel_data = analysis.get('PriceChannels', {})
        trend_data = analysis.get('TrendAnalysis', {})
        pattern_data = analysis.get('ClassicPatterns', {})

        section = f"⏰ فريم {timeframe} - {priority}\n\n"
        section += f"💵 السعر الحالي\n${current_price:,.2f}\n\n"

        # --- Supports ---
        section += "🎯 الدعوم\n"
        supports = sr_data.get('supports', [])
        if supports:
            section += f"🟢 دعم عند: ${supports[0]:,.2f}\n"
        lower_band = channel_data.get('lower_band')
        if lower_band:
            section += f"🟢 قناة سعرية دعم عند: ${lower_band:,.2f}\n"

        uptrend_line_data = analysis.get('TrendLineAnalysis', {}).get('uptrend')
        if uptrend_line_data:
            trend_line_price = uptrend_line_data['slope'] * len(analysis.get('df', [])) + uptrend_line_data['intercept']
            section += f"🟢 ترند عند دعم: ${trend_line_price:,.2f}\n"

        demand_zones = sr_data.get('all_demand_zones', [])
        if demand_zones:
            zone = demand_zones[0]
            section += f"🟢 مناطق الطلب: ${zone['start']:,.2f} - ${zone['end']:,.2f}\n"
        else:
            section += "🟢 مناطق الطلب: ❌ لا توجد مناطق طلب واضحة\n"

        fib_supports = analysis.get('FibonacciAnalysis', {}).get('supports', {})
        if fib_supports:
            fib_support_str = ', '.join([f"{k} (${v:,.2f})" for k, v in fib_supports.items()])
            section += f"🟢 مستويات فيبوناتشي دعم: {fib_support_str}\n"

        # --- Resistances ---
        section += "\n🔴 المقاومات\n"
        resistances = sr_data.get('resistances', [])
        if resistances:
            section += f"🔴 مقاومة عند: ${resistances[0]:,.2f}\n"
        upper_band = channel_data.get('upper_band')
        if upper_band:
            section += f"🔴 قناة سعرية مقاومة عند: ${upper_band:,.2f}\n"

        downtrend_line_data = analysis.get('TrendLineAnalysis', {}).get('downtrend')
        if downtrend_line_data:
            trend_line_price = downtrend_line_data['slope'] * len(analysis.get('df', [])) + downtrend_line_data['intercept']
            section += f"🔴 ترند عند مقاومة: ${trend_line_price:,.2f}\n"

        fib_resistances = analysis.get('FibonacciAnalysis', {}).get('resistances', {})
        if fib_resistances:
            fib_resistance_str = ', '.join([f"{k} (${v:,.2f})" for k, v in fib_resistances.items()])
            section += f"🔴 مستويات فيبوناتشي مقاومة: {fib_resistance_str}\n"

        supply_zones = sr_data.get('all_supply_zones', [])
        if supply_zones:
            zone = supply_zones[0]
            section += f"🔴 مناطق العرض: ${zone['start']:,.2f} - ${zone['end']:,.2f}\n"
        else:
            section += "🔴 مناطق العرض: ❌ لا توجد مناطق عرض واضحة\n"

        # --- Trend ---
        trend_direction_text = trend_data.get('trend_direction', 'Sideways')
        trend_emoji = {'Uptrend': '📈', 'Downtrend': '📉', 'Sideways': '🔄'}.get(trend_direction_text)
        trend_text = {'Uptrend': 'ترند صاعد', 'Downtrend': 'ترند هابط', 'Sideways': 'ترند عرضي'}.get(trend_direction_text)
        section += f"\n📈 الترند العام\n{trend_emoji} {trend_text}\n"

        # --- Pattern ---
        section += "\n📐 النموذج الفني\n"
        if pattern_data.get('found_patterns'):
            p = pattern_data['found_patterns'][0]
            section += f"{p.get('name')} - ({p.get('status', '')})\n"
            section += f"- 🎯 هدف النموذج: ${p.get('price_target', 0):,.2f}\n"
            section += f"- 🛑 وقف خسارة: ${p.get('stop_loss', 0):,.2f}\n"
            section += f"- ▶️ تفعيل النموذج: عند اختراق المقاومة ${p.get('activation_level', 0):,.2f}\n"
            section += f"- ❌ إلغاء النموذج: عند كسر الدعم ${p.get('invalidation_level', 0):,.2f}\n"
        else:
            section += "❌ لا يوجد نموذج فني واضح.\n"

        # --- Indicators ---
        indicators_score = analysis.get('TechnicalIndicators', {}).get('total_score', 0)
        indicator_rating, indicator_emoji = self._get_indicator_rating(indicators_score)
        section += f"\n📊 المؤشرات الفنية\nالإيجابية: ({indicator_rating}/5) {indicator_emoji}\n"

        # --- Scenarios ---
        section += "\n🎲 السيناريوهات المحتملة\n"
        confidence = result.get('confidence', 60)
        main_action = result.get('main_action', '')

        if 'شراء' in main_action:
            bull_prob = confidence
            bear_prob = max(10, (100 - bull_prob) / 2 - 5)
            neutral_prob = 100 - bull_prob - bear_prob
        elif 'بيع' in main_action:
            bear_prob = confidence
            bull_prob = max(10, (100 - bear_prob) / 2 - 5)
            neutral_prob = 100 - bull_prob - bear_prob
        else: # Neutral
            bull_prob = 40
            bear_prob = 40
            neutral_prob = 20

        bull_prob = round(max(0, bull_prob))
        bear_prob = round(max(0, bear_prob))
        neutral_prob = round(max(0, 100 - bull_prob - bear_prob))

        pattern = pattern_data.get('found_patterns')
        target = pattern[0].get('price_target', current_price * 1.05) if pattern else current_price * 1.05
        activation = pattern[0].get('activation_level', current_price * 1.01) if pattern else current_price * 1.01
        invalidation = pattern[0].get('invalidation_level', current_price * 0.99) if pattern else current_price * 0.99

        section += f"📈 السيناريو الصاعد ({bull_prob}%)**\n- اختراق المقاومة ${activation:,.2f} ➡️ الهدف الأول ${target:,.2f}\n\n"
        section += f"➡️ السيناريو المحايد ({neutral_prob}%)**\n- البقاء داخل النطاق ➡️ تداول عرضي بين ${invalidation:,.2f} – ${activation:,.2f}\n\n"
        section += f"📉 السيناريو الهابط ({bear_prob}%)**\n- كسر الدعم ${invalidation:,.2f} ➡️ الهدف الأول ${invalidation:,.2f}\n"

        return section

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "📋 الملخص التنفيذي والشامل\n\nلا توجد بيانات كافية."

        summary = "📋 الملخص التنفيذي والشامل\n\n"

        summary += "⭐ أقوى فريم للاختراق\n"
        timeframe_map = {
            '1m': 'قصير المدى', '3m': 'قصير المدى', '5m': 'قصير المدى',
            '15m': 'متوسط المدى', '30m': 'متوسط المدى', '1h': 'متوسط المدى',
            '4h': 'طويل المدى', '1d': 'طويل المدى'
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

        summary += f"📊 قصير المدى: {strongest_patterns.get('قصير المدى', 'N/A')}\n"
        summary += f"📊 متوسط المدى: {strongest_patterns.get('متوسط المدى', 'N/A')}\n"
        summary += f"📊 طويل المدى: {strongest_patterns.get('طويل المدى', 'N/A')}\n\n"

        summary += "🔍 نقاط المراقبة الحرجة\n"
        summary += "📈 اختراق المقاومة:\n"
        for res in ranked_results:
            patterns = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns')
            if patterns:
                pattern = patterns[0]
                if pattern.get('activation_level'):
                    summary += f"- {res.get('timeframe')}: ${pattern['activation_level']:,.2f}\n"

        summary += "\n📉 كسر الدعم:\n"
        for res in ranked_results:
            patterns = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns')
            if patterns:
                pattern = patterns[0]
                if pattern.get('invalidation_level'):
                    summary += f"- {res.get('timeframe')}: ${pattern['invalidation_level']:,.2f}\n"

        return summary

    def _format_final_recommendation(self, ranked_results: List[Dict]) -> str:
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec:
            return "🎯 التوصية النهائية\n\n❌ لا توجد توصية واضحة حاليًا."

        setup: TradeSetup = primary_rec['trade_setup']

        rec_text = "🎯 التوصية النهائية بعد دمج تحليل الفريمات الثلاثة\n\n"

        rec_text += "🚀 الدخول الأساسي\n"

        fib_resistances = primary_rec.get('raw_analysis', {}).get('FibonacciAnalysis', {}).get('resistances', {})
        fib_confluence = ""
        if fib_resistances:
            for level_name, level_price in fib_resistances.items():
                if abs(setup.entry_price - level_price) / setup.entry_price < 0.01:
                    fib_confluence = f" (تتوافق مع مستوى فيبوناتشي {level_name})"
                    break

        rec_text += f"▶️ عند اختراق المقاومة ${setup.entry_price:,.2f}{fib_confluence} مع تأكيد قوة المؤشرات على فريم {setup.timeframe}\n\n"

        rec_text += "🎯 الأهداف\n"
        rec_text += f"🥇 الهدف الأول: ${setup.target1:,.2f}\n"
        if setup.target2:
            rec_text += f"🥈 الهدف الثاني: ${setup.target2:,.2f}\n\n"

        rec_text += f"🛑 وقف الخسارة\n❌ عند كسر الدعم ${setup.stop_loss:,.2f} (فريم {setup.timeframe})\n\n"

        rec_text += f"✅ الدخول المؤكد\n"
        rec_text += f"📊 التأكيد: {setup.confirmation_condition}\n"
        rec_text += f"📈 الحالة: {setup.confirmation_status}\n\n"

        rec_text += "📋 تفاصيل الصفقة المؤكدة:\n"
        rec_text += f"💰 سعر الدخول: ${setup.entry_price:,.2f}\n"
        rec_text += f"🎯 الهدف الأول: ${setup.target1:,.2f}\n"
        if setup.target2:
            rec_text += f"🎯 الهدف الثاني: ${setup.target2:,.2f}\n"
        rec_text += f"🛑 وقف الخسارة: ${setup.stop_loss:,.2f}\n\n"

        rec_text += "❌ شروط إلغاء الدخول المؤكد:\n"
        for condition in setup.invalidation_conditions:
            rec_text += f"🚨 {condition}\n"

        rec_text += "\n🔄 استراتيجية دعم الفريمات\n"
        for res in ranked_results:
            if res.get('trade_setup') and res['trade_setup'] != setup:
                other_setup = res['trade_setup']
                rec_text += f"📊 متابعة فريم {other_setup.timeframe} لاختراق ${other_setup.entry_price:,.2f} للأهداف ${other_setup.target1:,.2f}\n"

        rec_text += "\n⚠️ ملاحظات مهمة\n🚨 إذا أي فريم يعطي إشارة عكسية قوية (كسر الدعم أو ضعف المؤشرات) ➡️ إعادة تقييم الدخول أو ضبط وقف الخسارة"

        return rec_text
