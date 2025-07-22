# main.py
# این اسکریپت پایتون منطق اصلی به‌هم‌ریختن و فیلتر کردن تنظیمات اشتراک را پیاده‌سازی می‌کند.
# اکنون تنظیمات را از فایل config.txt می‌خواند و خروجی را در یک فایل مشخص می‌نویسد.
# این نسخه در صورت بروز مشکل در واکشی یک URL، به URL بعدی می‌رود و فرایند را متوقف نمی‌کند.
# همچنین، امکان تنظیمات جداگانه (type و count_per_url) برای هر URL را فراهم می‌کند.
# پشتیبانی از GLOBAL_COUNT=0 برای انتخاب نامحدود.

import base64    # برای کدگذاری و رمزگشایی Base64
import os        # برای کار با مسیرها و سیستم فایل
import random    # برای به‌هم‌ریختن آرایه
import sys       # برای خروج از اسکریپت در صورت خطا
import requests  # برای واکشی URLها (نیاز به نصب: pip install requests)

# تابع کمکی: بررسی می‌کند که آیا یک رشته Base64 معتبر است یا خیر
def is_base64(s):
    try:
        # بررسی می‌کند که طول رشته مضربی از 4 باشد (شامل Padding)
        if len(s) % 4 != 0:
            return False
        # تلاش برای رمزگشایی و سپس رمزگذاری مجدد برای بررسی تطابق
        return base64.b64encode(base64.b64decode(s)).decode('utf-8') == s
    except Exception:
        return False

# تابع کمکی: یک رشته UTF-8 را به Base64 کدگذاری می‌کند
def encode_base64(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

# تابع کمکی: یک رشته Base64 را به UTF-8 رمزگشایی می‌کند
def decode_base64(s):
    return base64.b64decode(s).decode('utf-8')

# تابع کمکی: الگوریتم Fisher-Yates برای به‌هم‌ریختن آرایه
def shuffle_array(arr):
    random.shuffle(arr) # تابع داخلی random.shuffle این کار را انجام می‌دهد

# تابع برای خواندن فایل پیکربندی config.txt
def read_config(config_file_path):
    config = {}
    target_urls_section = False
    target_urls_list = []

    with open(config_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): # نادیده گرفتن خطوط خالی یا کامنت
                continue

            if line == "TARGET_URLS=": # شروع بخش URLها
                target_urls_section = True
                continue

            if target_urls_section:
                # اگر خط یک URL است (شروع با http/https)
                if line.startswith('http://') or line.startswith('https://'):
                    parts = line.split(',', 1) # جدا کردن URL از پارامترها
                    url = parts[0].strip()
                    url_config = {'url': url}

                    if len(parts) > 1:
                        params_str = parts[1].strip()
                        params = params_str.split(',')
                        for param in params:
                            if '=' in param:
                                key, value = param.split('=', 1)
                                if key.strip() == 'type':
                                    url_config['type'] = value.strip()
                                elif key.strip() == 'count_per_url':
                                    try:
                                        url_config['count_per_url'] = int(value.strip())
                                    except ValueError:
                                        print(f"هشدار: مقدار 'count_per_url' نامعتبر برای URL: {url}", file=sys.stderr)
                    target_urls_list.append(url_config)
                else: # اگر خط دیگر یک URL نیست، بخش URLها به پایان رسیده است
                    target_urls_section = False
                    # پردازش خط فعلی به عنوان یک تنظیم عادی
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            else: # پردازش خطوط تنظیمات عادی
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

    config['targetUrls'] = target_urls_list
    return config

# تابع اصلی اجرا که توسط گیت‌هاب اکشن فراخوانی می‌شود
def run():
    try:
        # خواندن تنظیمات از فایل config.txt
        config_path = os.path.join(os.getcwd(), 'config.txt')
        config = read_config(config_path)

        # تبدیل مقادیر به نوع صحیح
        global_count_str = config.get('GLOBAL_COUNT', '300')
        global_count = int(global_count_str) if global_count_str.isdigit() else 0 # اگر 0 باشد، نامحدود است
        global_type_param = config.get('GLOBAL_TYPE', '')
        output_folder = config.get('OUTPUT_FOLDER', 'shuffled_outputs')
        output_file_name = config.get('OUTPUT_FILE_NAME', 'shuffled_configs.txt')
        target_urls_configs = config.get('targetUrls', [])

        print(f"تعداد نهایی مورد نیاز: {'نامحدود' if global_count == 0 else global_count}")
        if global_type_param:
            print(f"فیلتر نوع سراسری: {global_type_param}")
        print(f"فایل خروجی در: {output_folder}/{output_file_name}")

        all_valid_lines = [] # لیستی برای ذخیره تمام خطوط معتبر از همه URLها

        if not target_urls_configs:
            print("خطا: لیست 'targetUrls' در config.txt خالی است یا وجود ندارد.", file=sys.stderr)
            sys.exit(1)

        for url_config in target_urls_configs:
            current_url = url_config.get('url')
            if not current_url:
                print(f"هشدار: یک شیء URL در config.txt فاقد 'url' است. نادیده گرفته شد.", file=sys.stderr)
                continue

            # استفاده از تنظیمات خاص URL، در غیر این صورت از تنظیمات سراسری استفاده می‌کند
            current_type_param = url_config.get('type', global_type_param)
            current_count_per_url = url_config.get('count_per_url') # این count فقط برای این URL است

            print(f"\nدر حال واکشی از URL: {current_url}")
            if current_type_param:
                print(f"  فیلتر نوع خاص برای این URL: {current_type_param}")
            if current_count_per_url is not None:
                print(f"  تعداد خطوط برای انتخاب از این URL: {current_count_per_url}")

            try:
                # واکشی محتوا از URL مقصد
                response = requests.get(current_url, timeout=10) # اضافه کردن timeout برای جلوگیری از توقف طولانی
                response.raise_for_status() # در صورت پاسخ‌های بد (4xx یا 5xx) خطا ایجاد می‌کند

                text = response.text
                print(f"  طول محتوای واکشی شده: {len(text)}")

                # اگر محتوا Base64 باشد، آن را رمزگشایی می‌کند
                if is_base64(text.strip()):
                    print('  محتوا به عنوان Base64 شناسایی شد، در حال رمزگشایی...')
                    text = decode_base64(text.strip())

                # تقسیم محتوا به خطوط و فیلتر کردن خطوط خالی یا نظرات
                current_lines = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('#')]
                print(f"  تعداد خطوط معتبر اولیه از این URL: {len(current_lines)}")

                # اگر پارامتر type خاص برای این URL مشخص شده باشد، خطوط را فیلتر می‌کند
                if current_type_param:
                    types = [t.strip().lower() for t in current_type_param.split(',')]
                    current_lines = [line for line in current_lines if any(line.lower().startswith(f"{t}://") for t in types)]
                    print(f"  تعداد خطوط پس از فیلتر نوع از این URL: {len(current_lines)}")

                # اگر count_per_url برای این URL مشخص شده باشد، به همان تعداد خط انتخاب می‌کند
                if current_count_per_url is not None:
                    shuffle_array(current_lines) # ابتدا خطوط این URL را به‌هم‌می‌ریزد
                    current_lines = current_lines[:current_count_per_url]
                    print(f"  تعداد خطوط انتخاب شده از این URL (بر اساس count_per_url): {len(current_lines)}")

                all_valid_lines.extend(current_lines) # اضافه کردن خطوط معتبر به لیست کلی

            except requests.exceptions.Timeout:
                print(f"  خطا: واکشی URL '{current_url}' به دلیل اتمام زمان متوقف شد.", file=sys.stderr)
            except requests.exceptions.RequestException as e:
                print(f"  خطا در واکشی URL '{current_url}': {e}", file=sys.stderr)
            except Exception as e:
                print(f"  خطای غیرمنتظره در پردازش URL '{current_url}': {e}", file=sys.stderr)

        print(f"\nتعداد کل خطوط معتبر جمع‌آوری شده از همه URLهای موفق: {len(all_valid_lines)}")

        # اگر هیچ خط معتبری پس از جمع‌آوری یافت نشد
        if not all_valid_lines:
            print('هیچ خط تنظیمات معتبری از همه URLها یافت نشد. فایل خروجی خالی خواهد بود.')
            # همچنان فایل خروجی خالی ایجاد می‌شود
            pass

        shuffle_array(all_valid_lines) # به‌هم‌ریختن آرایه خطوط جمع‌آوری شده
        print('خطوط نهایی به‌هم‌ریخته شدند.')

        # انتخاب تعداد مشخصی از خطوط از لیست کلی (بر اساس global_count)
        # اگر global_count برابر 0 باشد، همه خطوط انتخاب می‌شوند (نامحدود)
        if global_count == 0:
            selected_lines = all_valid_lines
        else:
            selected_lines = all_valid_lines[:global_count]
        print(f"تعداد {len(selected_lines)} خط نهایی برای خروجی انتخاب شد.")

        # اتصال خطوط انتخاب شده و کدگذاری نهایی به Base64
        final_text = "\r\n".join(selected_lines)
        base64_data = encode_base64(final_text)

        # ایجاد پوشه خروجی اگر وجود ندارد
        full_output_path = os.path.join(os.getcwd(), output_folder)
        os.makedirs(full_output_path, exist_ok=True) # exist_ok=True از خطا در صورت وجود پوشه جلوگیری می‌کند
        print(f"پوشه خروجی ایجاد شد: {full_output_path}")

        # نوشتن خروجی به فایل
        output_file = os.path.join(full_output_path, output_file_name)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(base64_data)
        print(f"خروجی در فایل ذخیره شد: {output_file}")

    except FileNotFoundError:
        print(f"خطا: فایل پیکربندی config.txt یافت نشد.", file=sys.stderr)
        sys.exit(1) # خروج با کد خطا
    except Exception as e:
        print(f"اکشن با خطا مواجه شد: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()
