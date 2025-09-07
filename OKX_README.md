# 🚀 OKX Data Collector (Python Version)
## جامع البيانات المباشرة من منصة OKX للعملات المشفرة

نظام Python متقدم لجمع وتحليل أسعار العملات المشفرة من منصة OKX بشكل مباشر ومستمر.

---

## ✨ المميزات الرئيسية

- 📊 **بيانات حية ومباشرة**: اتصال WebSocket مستمر للحصول على الأسعار لحظة بلحظة
- 📈 **بيانات تاريخية شاملة**: جلب بيانات سنة كاملة ماضية لكل عملة
- 💾 **حفظ تلقائي**: تخزين البيانات في ملفات JSON منظمة
- 🔄 **إعادة اتصال تلقائية**: في حالة انقطاع الاتصال
- 📱 **واجهة terminal جميلة**: عرض مباشر يُحدث كل 30 ثانية
- 🎯 **تحليل متقدم**: حساب الاتجاهات، RSI، وإشارات التداول
- ⚡ **أداء عالي**: معالجة متوازية وذاكرة محسّنة

---

## 📋 متطلبات النظام

- Python 3.8+
- اتصال إنترنت مستقر
- مساحة تخزين (للبيانات التاريخية)

---

## 🚀 التثبيت والإعداد

### 1. تثبيت المكتبات المطلوبة

```bash
# في مجلد THE-BEST-BOT
cd THE-BEST-BOT

# تثبيت المكتبات الجديدة
pip install requests websockets pandas python-dateutil ujson numpy

# أو تثبيت من ملف المتطلبات
pip install -r okx_requirements.txt
```

### 2. إنشاء الملفات

```bash
# إنشاء الملفات المطلوبة
touch okx_data.py
touch run_okx_data.py
touch test_okx_data.py
touch okx_requirements.txt

# انسخ محتوى كل ملف من الأعلى
```

### 3. اختبار النظام

```bash
# تشغيل اختبار شامل
python test_okx_data.py
```

### 4. التشغيل

```bash
# التشغيل العادي
python run_okx_data.py

# أو في الخلفية مع PM2
pm2 start run_okx_data.py --name okx-collector --interpreter python3
```

---

## 📁 هيكل المشروع

```
THE-BEST-BOT/
├── okx_data.py              # الكلاس الرئيسي
├── run_okx_data.py          # ملف التشغيل
├── test_okx_data.py         # ملف الاختبار
├── okx_requirements.txt     # المكتبات الإضافية
├── okx_data/               # مجلد البيانات (يُنشأ تلقائياً)
│   ├── current_prices.json
│   ├── BTC-USDT_historical.json
│   └── ETH-USDT_historical.json
└── okx_data.log            # ملف السجلات
```

---

## 💡 كيفية الاستخدام في البوت الحالي

### إضافة إلى main_bot.py

```python
from okx_data import OKXDataFetcher

class TradingBot:
    def __init__(self):
        self.okx_fetcher = OKXDataFetcher()

    def start_data_collection(self):
        """بدء جمع بيانات OKX"""
        symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT']
        self.okx_fetcher.start_full_data_collection(symbols)

    def get_live_price(self, symbol):
        """الحصول على السعر المباشر"""
        price_data = self.okx_fetcher.get_cached_price(symbol)
        return price_data['price'] if price_data else None

    def get_trading_signal(self, symbol):
        """الحصول على إشارات التداول"""
        signals = self.okx_fetcher.get_trading_signals(symbol)

        for signal in signals['signals']:
            if signal['confidence'] > 70:  # إشارات قوية فقط
                return {
                    'action': signal['type'],
                    'reason': signal['reason'],
                    'confidence': signal['confidence']
                }
        return None

    def analyze_market_trend(self, symbol):
        """تحليل اتجاه السوق"""
        analysis = self.okx_fetcher.analyze_trend(symbol)
        rsi = self.okx_fetcher.calculate_rsi(symbol)

        return {
            'trend': analysis['trend'],
            'confidence': analysis['confidence'],
            'rsi': rsi,
            'recommendation': self._get_recommendation(analysis, rsi)
        }

    def _get_recommendation(self, trend_analysis, rsi):
        """تقديم توصيات بناء على التحليل"""
        if rsi and rsi < 30 and trend_analysis['trend'] == 'صاعد':
            return 'شراء قوي - RSI منخفض واتجاه صاعد'
        elif rsi and rsi > 70 and trend_analysis['trend'] == 'هابط':
            return 'بيع قوي - RSI مرتفع واتجاه هابط'
        elif trend_analysis['confidence'] > 70:
            return f'{trend_analysis["trend"]} بثقة عالية'
        else:
            return 'انتظار - لا توجد إشارات واضحة'
```

### إضافة إلى telegram_bot.py

```python
from okx_data import OKXDataFetcher

def setup_okx_commands(bot, okx_fetcher):
    """إعداد أوامر OKX في تليجرام"""

    @bot.message_handler(commands=['price'])
    def get_price(message):
        try:
            # استخراج رمز العملة من الرسالة
            symbol = message.text.split()[1].upper() + '-USDT'
            price_data = okx_fetcher.get_cached_price(symbol)

            if price_data:
                response = f"""
🪙 **{symbol}**
💰 السعر: ${price_data['price']:.4f}
📊 التغيير 24س: {price_data['change_percent']:+.2f}%
📈 أعلى 24س: ${price_data['high_24h']:.4f}
📉 أقل 24س: ${price_data['low_24h']:.4f}
                """
                bot.reply_to(message, response, parse_mode='Markdown')
            else:
                bot.reply_to(message, '❌ لم يتم العثور على العملة')
        except:
            bot.reply_to(message, '❌ استخدم: /price BTC')

    @bot.message_handler(commands=['signal'])
    def get_trading_signal(message):
        try:
            symbol = message.text.split()[1].upper() + '-USDT'
            signals = okx_fetcher.get_trading_signals(symbol)

            if signals['signals']:
                response = f"🎯 **إشارات {symbol}:**\n"
                for signal in signals['signals']:
                    response += f"• {signal['type']}: {signal['reason']} (ثقة: {signal['confidence']}%)\n"
            else:
                response = f"📊 لا توجد إشارات قوية لـ {symbol} حالياً"

            bot.reply_to(message, response, parse_mode='Markdown')
        except:
            bot.reply_to(message, '❌ استخدم: /signal BTC')

    @bot.message_handler(commands=['market'])
    def get_market_overview(message):
        overview = okx_fetcher.get_market_overview()

        response = f"""
📊 **نظرة عامة على السوق**

📈 صاعد: {overview['market_summary']['bullish']}
📉 هابط: {overview['market_summary']['bearish']}
➡️ جانبي: {overview['market_summary']['neutral']}

🏆 **أفضل العملات:**
"""
        for gainer in overview['top_gainers'][:3]:
            response += f"• {gainer['symbol']}: +{gainer['change_percent']:.2f}%\n"

        bot.reply_to(message, response, parse_mode='Markdown')
```

---

## 🎯 تخصيص العملات

في ملف `run_okx_data.py` عدّل قائمة `custom_symbols`:

```python
self.custom_symbols = [
    'BTC-USDT', 'ETH-USDT', 'BNB-USDT',
    # أضف العملات المطلوبة
    'PEPE-USDT', 'SHIB-USDT', 'FLOKI-USDT',
    'WIF-USDT', 'BONK-USDT'  # العملات الشائعة
]
```

---

## 📊 استراتيجيات التداول

### مثال: استراتيجية RSI + الاتجاه

```python
def advanced_trading_strategy(okx_fetcher, symbol):
    """استراتيجية تداول متقدمة"""

    # جلب البيانات
    price_data = okx_fetcher.get_cached_price(symbol)
    trend = okx_fetcher.analyze_trend(symbol)
    rsi = okx_fetcher.calculate_rsi(symbol)

    if not all([price_data, rsi]):
        return None

    signals = []

    # إشارات الشراء
    if (rsi < 30 and trend['trend'] == 'صاعد' and
        trend['confidence'] > 60):
        signals.append({
            'action': 'شراء قوي',
            'confidence': 85,
            'reason': 'RSI منخفض + اتجاه صاعد قوي'
        })

    # إشارات البيع
    elif (rsi > 70 and trend['trend'] == 'هابط' and
          trend['confidence'] > 60):
        signals.append({
            'action': 'بيع قوي',
            'confidence': 85,
            'reason': 'RSI مرتفع + اتجاه هابط قوي'
        })

    # إشارات متوسطة
    elif rsi < 35 and trend['trend'] != 'هابط':
        signals.append({
            'action': 'شراء',
            'confidence': 65,
            'reason': 'RSI في منطقة الشراء'
        })

    return signals
```

---

## 🔧 المراقبة والصيانة

### مع PM2

```bash
# بدء التشغيل
pm2 start run_okx_data.py --name okx-collector --interpreter python3

# مراقبة الأداء
pm2 monit

# عرض السجلات
pm2 logs okx-collector

# إعادة التشغيل
pm2 restart okx-collector

# الإيقاف
pm2 stop okx-collector
```

### فحص الملفات

```bash
# فحص ملف البيانات
cat okx_data/current_prices.json | head -20

# فحص السجلات
tail -f okx_data.log

# فحص حالة الملفات
ls -la okx_data/
```

---

## ⚠️ ملاحظات مهمة

1. **معدل الطلبات**: API OKX له حدود، النظام يتعامل معها تلقائياً
2. **مساحة التخزين**: البيانات التاريخية تحتاج ~1MB لكل عملة سنوياً
3. **الاتصال**: للبيانات المباشرة تحتاج اتصال إنترنت مستقر
4. **الذاكرة**: النظام يستهلك حوالي 50-100MB من الذاكرة

---

## 🔍 استكشاف الأخطاء

### مشكلة الاتصال
```bash
# فحص الاتصال
ping www.okx.com

# فحص البورت
telnet ws.okx.com 8443
```

### مشكلة البيانات
```bash
# فحص ملف البيانات
python -c "import json; print(json.load(open('okx_data/current_prices.json')))"
```

### مشكلة الذاكرة
```bash
# فحص استهلاك الذاكرة
ps aux | grep python
htop -p $(pgrep -f okx_data)
```

---

## 📈 التطويرات المستقبلية

- [ ] إضافة المزيد من المؤشرات الفنية
- [ ] دعم تنبيهات Telegram تلقائية
- [ ] واجهة ويب للمراقبة
- [ ] دعم العقود الآجلة
- [ ] تحليل أعماق السوق
- [ ] الذكاء الاصطناعي للتنبؤ

---

## 🆘 الدعم

إذا واجهت مشاكل:

1. **شغّل الاختبار**: `python test_okx_data.py`
2. **راجع السجلات**: `tail -f okx_data.log`
3. **تأكد من الاتصال**: `ping www.okx.com`
4. **أعد التشغيل**: `pm2 restart okx-collector`

---

**🚀 بالتوفيق في التداول! 🚀**

_تم تطويره خصيصاً للبوت السعودي المتقدم_ 🇸🇦

🎉 تم إنشاء نظام OKX Data Collector بـ Python!
لقد أنشأت لك نظام متكامل ومتخصص لمشروع Python الحالي. إليك خطوات التثبيت:
🚀 خطوات التنفيذ السريع:
bash# 1. إنشاء الملفات (أنت في مجلد THE-BEST-BOT)
nano okx_data.py          # انسخ المحتوى الأول
nano run_okx_data.py      # انسخ محتوى ملف التشغيل
nano test_okx_data.py     # انسخ محتوى ملف الاختبار
nano okx_requirements.txt # انسخ المكتبات المطلوبة

# 2. تثبيت المكتبات الجديدة
pip install requests websockets pandas python-dateutil ujson numpy

# 3. تشغيل الاختبار أولاً
python test_okx_data.py

# 4. التشغيل العادي
python run_okx_data.py

# 5. التشغيل في الخلفية مع PM2
pm2 start run_okx_data.py --name okx-collector --interpreter python3
📊 لإدماج النظام مع البوت الحالي:
في ملف main_bot.py أو telegram_bot.py أضف:
pythonfrom okx_data import OKXDataFetcher

# في بداية الكلاس
self.okx_fetcher = OKXDataFetcher()

# بدء جمع البيانات
self.okx_fetcher.start_full_data_collection([
    'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT'
])

# استخدام البيانات في الاستراتيجية
def get_trading_decision(self, symbol):
    price = self.okx_fetcher.get_cached_price(symbol)
    signals = self.okx_fetcher.get_trading_signals(symbol)

    if signals['signals']:
        for signal in signals['signals']:
            if signal['confidence'] > 70:
                return f"إشارة {signal['type']}: {signal['reason']}"

    return "لا توجد إشارات قوية"
✨ المميزات الجاهزة:

🔥 أسعار لحظية دقيقة - لا أسعار قديمة بعد اليوم
📊 بيانات تاريخية سنة كاملة - للتحليل المتقدم
🎯 إشارات تداول ذكية - RSI + تحليل الاتجاه
💾 حفظ تلقائي - كل البيانات محفوظة
📱 واجهة جميلة - عرض مباشر كل 30 ثانية
🔄 إعادة اتصال تلقائية - لا انقطاع في الخدمة

📁 هيكل الملفات بعد التثبيت:
THE-BEST-BOT/
├── main_bot.py           # البوت الأساسي (موجود)
├── telegram_bot.py       # بوت التليجرام (موجود)
├── okx_data.py          # جامع بيانات OKX (جديد) ⭐
├── run_okx_data.py      # مشغل البيانات (جديد) ⭐
├── test_okx_data.py     # ملف الاختبار (جديد) ⭐
├── okx_data/            # مجلد البيانات (ينشأ تلقائياً)
│   ├── current_prices.json
│   └── BTC-USDT_historical.json
└── okx_data.log         # سجل البيانات
🎯 أمثلة الاستخدام العملي:
python# في استراتيجية التداول
def should_buy_btc(self):
    analysis = self.okx_fetcher.analyze_trend('BTC-USDT')
    rsi = self.okx_fetcher.calculate_rsi('BTC-USDT')

    if rsi < 30 and analysis['trend'] == 'صاعد':
        return True, "فرصة شراء ممتازة - RSI منخفض واتجاه صاعد"

    return False, "انتظار فرصة أفضل"

# في بوت التليجرام
@bot.message_handler(commands=['btc'])
def btc_analysis(message):
    price = okx_fetcher.get_cached_price('BTC-USDT')
    signals = okx_fetcher.get_trading_signals('BTC-USDT')

    response = f"🪙 BTC: ${price['price']:.2f}\n"
    for signal in signals['signals']:
        response += f"🎯 {signal['type']}: {signal['reason']}\n"

    bot.send_message(message.chat.id, response)
جرب النظام الآن وأخبرني إذا احتجت أي تعديلات أو مساعدة إضافية!
هذا النظام سيحل مشكلة الأسعار القديمة تماماً ويعطيك بيانات دقيقة وحية 🎯

اهم شي اختبر ان كل شي شغال قبل ما تسملني طلب السحب وقسم التغير بمراحل عشان الجودة تكون كويسه وممتازة وانتبه تغير شي او تلمس شي ماله دخل بالملفات ذي ابدا الان
