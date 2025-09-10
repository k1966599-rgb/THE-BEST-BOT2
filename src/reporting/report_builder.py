from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup

class ReportBuilder:
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> Dict[str, Any]:
        header = self._format_header(general_info)

        # --- Group results by time horizon ---
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        horizon_map = {tf: horizon for horizon, tfs in timeframe_groups.items() for tf in tfs}
        grouped_results = {'long': [], 'medium': [], 'short': []}
        for res in ranked_results:
            horizon = horizon_map.get(res.get('timeframe'))
            if horizon:
                # Add symbol to result for use in formatting
                res['symbol'] = general_info.get('symbol', 'N/A')
                grouped_results[horizon].append(res)

        # --- Format sections for each horizon ---
        horizon_reports = {}
        for horizon, name in [('long', 'طويل المدى'), ('medium', 'متوسط المدى'), ('short', 'قصير المدى')]:
            results_in_horizon = grouped_results[horizon]
            if results_in_horizon:
                # Sort results within the horizon by the original ranking
                sorted_results = sorted(results_in_horizon, key=lambda x: ranked_results.index(x))
                horizon_reports[f"{horizon}_report"] = "\n\n".join(
                    [self._format_timeframe_section(res, f"الأولوية {i+1}") for i, res in enumerate(sorted_results)]
                )

        summary = self._format_summary(ranked_results)
        final_recommendation = self._format_final_recommendation(ranked_results)

        report = {
            "header": header,
            **horizon_reports,
            "summary": summary,
            "final_recommendation": final_recommendation,
            "ranked_results": ranked_results  # Pass the raw results back
        }
        return report

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
        timeframe = result.get('timeframe', 'N/A').upper()
        symbol = result.get('symbol', 'N/A')
        analysis = result.get('raw_analysis', {})
        current_price = result.get('current_price', 0)
        pattern_data = analysis.get('ClassicPatterns', {}).get('found_patterns', [])
        fib_data = analysis.get('FibonacciAnalysis', {})
        new_sr_data = analysis.get('NewSupportResistance', {})
        channel_data = analysis.get('PriceChannels', {})
        trend_line_data = analysis.get('TrendLineAnalysis', {})

        section = f"🕐 فريم {timeframe} — {symbol}\n"
        section += f"السعر الحالي: ${current_price:,.2f}\n\n"

        # --- Technical Pattern ---
        if pattern_data:
            p = pattern_data[0]
            section += f"📊 النموذج الفني: {p.get('name', 'N/A')} — {p.get('status', 'N/A')}\n\n"
            section += f"شروط التفعيل: اختراق المقاومة ${p.get('activation_level', 0):,.2f} مع ثبات شمعة {timeframe} فوقها\n\n"
            section += f"شروط الإلغاء: كسر الدعم ${p.get('invalidation_level', 0):,.2f} مع إغلاق شمعة {timeframe} تحته\n\n"
        else:
            section += "📊 النموذج الفني: لا يوجد نموذج واضح حاليًا.\n\n"

        # --- Supports ---
        section += "🟢 الدعوم\n\n"
        supports = new_sr_data.get('supports', [])
        if trend_line_data.get('support_trendline_price'):
            section += f"دعم ترند قصير: ${trend_line_data['support_trendline_price']:,.2f} (حرج)\n\n"
        if channel_data.get('lower_band'):
            section += f"دعم قناة سعرية: ${channel_data['lower_band']:,.2f} (قاع)\n\n"
        if fib_data.get('supports'):
            for level, price in fib_data['supports'].items():
                desc = "(قوي)" if level == '0.618' else "(متوسط)"
                section += f"دعم فيبو {level}: ${price:,.2f} {desc}\n\n"
        if supports:
            for s in supports:
                section += f"{s.get('description', 'دعم')}: ${s.get('level', 0):,.2f}\n\n"

        # --- Resistances ---
        section += "🔴 المقاومات\n\n"
        resistances = new_sr_data.get('resistances', [])
        if resistances:
            # The first resistance is the most critical one to break for pattern activation
            section += f"مقاومة رئيسية: ${resistances[0].get('level', 0):,.2f} (حرجة)\n\n"
        if pattern_data:
             section += f"مقاومة هدف النموذج: ${pattern_data[0].get('price_target', 0):,.2f} (فني)\n\n"
        if fib_data.get('resistances'):
            # Find the first extension level
            ext_res = next((price for level, price in fib_data['resistances'].items() if 'ext' in level), None)
            if ext_res:
                section += f"مقاومة فيبو امتداد: ${ext_res:,.2f} (قوية)\n\n"
        if resistances:
            for r in resistances:
                if "تاريخية" in r.get('description', ''):
                     section += f"منطقة عرض عالية: ${r.get('level', 0):,.2f} (تاريخية)\n\n"
        return section

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "📌 الملخص التنفيذي والشامل\n\nلا توجد بيانات كافية."

        summary = "📌 الملخص التنفيذي والشامل\n\n"
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})

        # Invert the groups for easier lookup
        horizon_map = {tf: horizon for horizon, tfs in timeframe_groups.items() for tf in tfs}

        # Group results by horizon
        grouped_results = {'long': [], 'medium': [], 'short': []}
        for res in ranked_results:
            horizon = horizon_map.get(res.get('timeframe'))
            if horizon:
                grouped_results[horizon].append(res)

        # Build the summary string for each horizon
        for horizon, name in [('long', 'طويل المدى'), ('medium', 'متوسط المدى'), ('short', 'قصير المدى')]:
            results_in_horizon = grouped_results[horizon]
            if not results_in_horizon:
                continue

            # Find the highest-ranked result in this horizon
            best_res = results_in_horizon[0]
            pattern_data = best_res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [])

            if pattern_data:
                p = pattern_data[0]
                # Assuming target1, target2, target3 exist in the pattern data
                targets = [t for t in [p.get('price_target'), p.get('target2'), p.get('target3')] if t]
                target_str = ' → '.join([f"${t:,.0f}" for t in targets])
                summary += f"{name} ({best_res.get('timeframe').upper()}): {p.get('name')} → اختراق ${p.get('activation_level', 0):,.0f} → أهداف: {target_str}\n\n"

        summary += "📌 نقاط المراقبة الحرجة:\n"

        # Breakout points
        summary += "اختراق المقاومة: "
        breakout_points = []
        for res in ranked_results:
            p_data = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [])
            if p_data:
                breakout_points.append(f"{res.get('timeframe').upper()} = ${p_data[0].get('activation_level', 0):,.0f}")
        summary += ', '.join(breakout_points) + "\n"

        # Breakdown points
        summary += "كسر الدعم: "
        breakdown_points = []
        for res in ranked_results:
            p_data = res.get('raw_analysis', {}).get('ClassicPatterns', {}).get('found_patterns', [])
            if p_data:
                breakdown_points.append(f"{res.get('timeframe').upper()} = ${p_data[0].get('invalidation_level', 0):,.0f}")
        summary += ', '.join(breakdown_points) + "\n"

        return summary

    def _format_final_recommendation(self, ranked_results: List[Dict]) -> str:
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec or not primary_rec.get('trade_setup'):
            return "📌 صفقة مؤكدة\n\n❌ لا توجد توصية واضحة بمواصفات كاملة حاليًا."

        setup: TradeSetup = primary_rec.get('trade_setup')
        rec_text = "📌 صفقة مؤكدة بعد دمج الفريمات الثلاثة\n\n"
        rec_text += f"سعر الدخول المبدئي: عند اختراق ${setup.entry_price:,.2f} (فريم {setup.timeframe.upper()}) {setup.confirmation_condition}\n\n"

        # Build targets string
        targets = [t for t in [setup.target1, setup.target2] if t]
        target_str = ' → '.join([f"${t:,.2f}" for t in targets])
        if len(targets) < 3: # Assuming a third potential target could exist
            potential_target = targets[-1] * 1.02 if targets else setup.entry_price * 1.05
            target_str += f" → تمدد محتمل ${potential_target:,.2f}"
        rec_text += f"الأهداف: {target_str}\n\n"

        rec_text += f"وقف الخسارة: عند كسر ${setup.stop_loss:,.2f} (فريم {setup.timeframe.upper()})\n\n"

        # Supporting timeframes strategy
        rec_text += "استراتيجية دعم الفريمات:\n"
        supporting_recs = [r for r in ranked_results if r.get('trade_setup') and r['trade_setup'] != setup]
        if supporting_recs:
            for res in supporting_recs:
                other_setup = res['trade_setup']
                other_targets = [t for t in [other_setup.target1, other_setup.target2] if t]
                other_target_str = ' – '.join([f"${t:,.2f}" for t in other_targets])
                rec_text += f"متابعة فريم {other_setup.timeframe.upper()} لاختراق ${other_setup.entry_price:,.2f} → أهداف {other_target_str}\n"
        else:
            rec_text += "لا توجد فريمات أخرى داعمة حاليًا.\n"

        return rec_text
