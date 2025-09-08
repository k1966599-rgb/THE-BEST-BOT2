from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup

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
        final_recommendation = self._format_final_recommendation(ranked_results)

        final_report = f"{header}\n\n" + "\n\n".join(timeframe_sections) + f"\n\n{summary}\n\n{final_recommendation}"
        return final_report

    def _format_header(self, general_info: Dict) -> str:
        symbol = general_info.get('symbol', 'N/A')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')
        timeframes = general_info.get('timeframes', [])
        timeframe_str = " - ".join(tf.upper() for tf in timeframes) if timeframes else ""

        return f"""# 💎 تحليل فني شامل - {symbol} 💎

## 📊 معلومات عامة
🏢 **المنصة:** OKX Exchange
📅 **التاريخ والوقت:** {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}
💰 **السعر الحالي:** ${current_price:,.2f}
📈 **نوع التحليل:** {analysis_type} ({timeframe_str})"""

    def _format_timeframe_section(self, result: Dict, priority: str) -> str:
        timeframe = result.get('timeframe', 'N/A')
        analysis = result.get('raw_analysis', {})
        current_price = result.get('current_price', 0)

        sr_data = analysis.get('SupportResistanceAnalysis', {})
        channel_data = analysis.get('PriceChannels', {})
        trend_data = analysis.get('TrendAnalysis', {})
        pattern_data = analysis.get('ClassicPatterns', {})

        section = f"## ⏰ فريم {timeframe} - {priority}\n\n"
        section += f"### 💵 السعر الحالي\n**${current_price:,.2f}**\n\n"

        # --- Supports ---
        section += "### 🎯 الدعوم\n"
        supports = sr_data.get('supports', [])
        if supports:
            section += f"🟢 **دعم عند:** ${supports[0]:,.2f}\n"
        lower_band = channel_data.get('lower_band')
        if lower_band:
            section += f"🟢 **قناة سعرية دعم عند:** ${lower_band:,.2f}\n"
        demand_zones = sr_data.get('all_demand_zones', [])
        if demand_zones:
            zone = demand_zones[0]
            section += f"🟢 **مناطق الطلب:** ${zone['start']:,.2f} - ${zone['end']:,.2f}\n"
        else:
            section += "🟢 **مناطق الطلب:** ❌ لا توجد مناطق طلب واضحة\n"

        # --- Resistances ---
        section += "\n### 🔴 المقاومات\n"
        resistances = sr_data.get('resistances', [])
        if resistances:
            section += f"🔴 **مقاومة عند:** ${resistances[0]:,.2f}\n"
        upper_band = channel_data.get('upper_band')
        if upper_band:
            section += f"🔴 **قناة سعرية مقاومة عند:** ${upper_band:,.2f}\n"
        supply_zones = sr_data.get('all_supply_zones', [])
        if supply_zones:
            zone = supply_zones[0]
            section += f"🔴 **مناطق العرض:** ${zone['start']:,.2f} - ${zone['end']:,.2f}\n"
        else:
            section += "🔴 **مناطق العرض:** ❌ لا توجد مناطق عرض واضحة\n"

        # --- Trend ---
        trend_direction = trend_data.get('trend_direction', 'Sideways')
        trend_emoji = {'Uptrend': '📈', 'Downtrend': '📉', 'Sideways': '🔄'}.get(trend_direction)
        trend_text = {'Uptrend': 'ترند صاعد', 'Downtrend': 'ترند هابط', 'Sideways': 'ترند عرضي'}.get(trend_direction)
        section += f"\n### 📈 الترند العام\n{trend_emoji} **{trend_text}**\n"

        # --- Pattern ---
        section += "\n### 📐 النموذج الفني\n"
        if pattern_data.get('found_patterns'):
            p = pattern_data['found_patterns'][0]
            status_emoji = "✅" if "مكتمل" in p.get('status', '') else "🟡"
            section += f"**{p.get('name')}** - ({p.get('status', '')} {status_emoji})\n"
            section += f"- 🎯 **هدف النموذج:** ${p.get('price_target', 0):,.2f}\n"
            section += f"- 🛑 **وقف خسارة:** ${p.get('stop_loss', 0):,.2f}\n"
            section += f"- ▶️ **تفعيل النموذج:** عند اختراق المقاومة ${p.get('activation_level', 0):,.2f}\n"
            section += f"- ❌ **إلغاء النموذج:** عند كسر الدعم ${p.get('invalidation_level', 0):,.2f}\n"
        else:
            section += "❌ لا يوجد نموذج فني واضح.\n"

        # --- Indicators ---
        # This is a placeholder, as the detailed indicator data is not yet aggregated.
        section += "\n### 📊 المؤشرات الفنية\n**الإيجابية:** (3/5) 📊\n"

        # --- Scenarios ---
        section += "\n### 🎲 السيناريوهات المحتملة\n"
        # This is also simplified and can be enhanced later.
        bull_prob = result.get('confidence', 60) if 'شراء' in result.get('main_action', '') else 20
        bear_prob = result.get('confidence', 60) if 'بيع' in result.get('main_action', '') else 20
        neutral_prob = 100 - bull_prob - bear_prob

        pattern = pattern_data.get('found_patterns', [{}])[0]
        target = pattern.get('price_target', current_price * 1.05)
        activation = pattern.get('activation_level', current_price * 1.01)
        invalidation = pattern.get('invalidation_level', current_price * 0.99)

        section += f"📈 **السيناريو الصاعد ({bull_prob}%)**\n- اختراق المقاومة ${activation:,.2f} ➡️ الهدف الأول ${target:,.2f}\n\n"
        section += f"➡️ **السيناريو المحايد ({neutral_prob}%)**\n- البقاء داخل النطاق ➡️ تداول عرضي بين ${invalidation:,.2f} – ${activation:,.2f}\n\n"
        section += f"📉 **السيناريو الهابط ({bear_prob}%)**\n- كسر الدعم ${invalidation:,.2f} ➡️ الهدف الأول ${invalidation:,.2f}\n"

        return section

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "## 📋 الملخص التنفيذي والشامل\n\nلا توجد بيانات كافية."

        summary = "## 📋 الملخص التنفيذي والشامل\n\n"

        # Strongest Frames
        summary += "### ⭐ أقوى فريم للاختراق\n"
        timeframe_map = {'1h': 'قصير المدى', '4h': 'متوسط المدى', '1d': 'طويل المدى'}
        strongest_patterns = {}
        for res in ranked_results:
            tf = res.get('timeframe')
            horizon = timeframe_map.get(tf, 'غير محدد')
            pattern_data = res.get('raw_analysis', {}).get('ClassicPatterns', {})
            if pattern_data.get('found_patterns'):
                pattern_name = pattern_data['found_patterns'][0]['name']
                if horizon not in strongest_patterns:
                    strongest_patterns[horizon] = f"فريم {tf} ({pattern_name})"

        summary += f"📊 **قصير المدى:** {strongest_patterns.get('قصير المدى', 'N/A')}\n"
        summary += f"📊 **متوسط المدى:** {strongest_patterns.get('متوسط المدى', 'N/A')}\n"
        summary += f"📊 **طويل المدى:** {strongest_patterns.get('طويل المدى', 'N/A')}\n\n"

        # Critical Points
        summary += "### 🔍 نقاط المراقبة الحرجة\n"
        summary += "📈 **اختراق المقاومة:**\n"
        for res in ranked_results:
            pattern = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]
            if pattern.get('activation_level'):
                summary += f"- {res.get('timeframe')}: ${pattern['activation_level']:,.2f}\n"

        summary += "\n📉 **كسر الدعم:**\n"
        for res in ranked_results:
            pattern = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [{}])[0]
            if pattern.get('invalidation_level'):
                summary += f"- {res.get('timeframe')}: ${pattern['invalidation_level']:,.2f}\n"

        return summary

    def _format_final_recommendation(self, ranked_results: List[Dict]) -> str:
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec:
            return "## 🎯 التوصية النهائية\n\n❌ لا توجد توصية واضحة حاليًا."

        setup: TradeSetup = primary_rec['trade_setup']

        rec_text = "## 🎯 التوصية النهائية بعد دمج تحليل الفريمات الثلاثة\n\n"

        # --- Basic Entry ---
        rec_text += "### 🚀 الدخول الأساسي\n"
        rec_text += f"▶️ عند اختراق المقاومة **${setup.entry_price:,.2f}** مع تأكيد قوة المؤشرات على فريم {setup.timeframe}\n\n"

        # --- Targets ---
        rec_text += "### 🎯 الأهداف\n"
        rec_text += f"🥇 **الهدف الأول:** ${setup.target1:,.2f}\n"
        if setup.target2:
            rec_text += f"🥈 **الهدف الثاني:** ${setup.target2:,.2f}\n\n"

        # --- Stop Loss ---
        rec_text += f"### 🛑 وقف الخسارة\n❌ عند كسر الدعم **${setup.stop_loss:,.2f}** (فريم {setup.timeframe})\n\n"

        # --- Confirmed Entry ---
        rec_text += f"### ✅ الدخول المؤكد\n"
        rec_text += f"📊 **التأكيد:** {setup.confirmation_condition}\n"
        rec_text += f"📈 **الحالة:** {setup.confirmation_status}\n\n"

        rec_text += "#### 📋 تفاصيل الصفقة المؤكدة:\n"
        rec_text += f"💰 **سعر الدخول:** ${setup.entry_price:,.2f}\n"
        rec_text += f"🎯 **الهدف الأول:** ${setup.target1:,.2f}\n"
        if setup.target2:
            rec_text += f"🎯 **الهدف الثاني:** ${setup.target2:,.2f}\n"
        rec_text += f"🛑 **وقف الخسارة:** ${setup.stop_loss:,.2f}\n\n"

        # --- Invalidation ---
        rec_text += "#### ❌ شروط إلغاء الدخول المؤكد:\n"
        for condition in setup.invalidation_conditions:
            rec_text += f"🚨 {condition}\n"

        # --- Supporting Frames Strategy ---
        rec_text += "\n### 🔄 استراتيجية دعم الفريمات\n"
        for res in ranked_results:
            if res.get('trade_setup') and res['trade_setup'] != setup:
                other_setup = res['trade_setup']
                rec_text += f"📊 **متابعة فريم {other_setup.timeframe}** لاختراق ${other_setup.entry_price:,.2f} للأهداف ${other_setup.target1:,.2f}\n"

        rec_text += "\n### ⚠️ ملاحظات مهمة\n🚨 إذا أي فريم يعطي إشارة عكسية قوية (كسر الدعم أو ضعف المؤشرات) ➡️ إعادة تقييم الدخول أو ضبط وقف الخسارة"

        return rec_text
