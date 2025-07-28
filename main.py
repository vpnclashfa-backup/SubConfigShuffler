# main.py
# این اسکریپت پایتون منطق اصلی به‌هم‌ریختن و فیلتر کردن تنظیمات اشتراک را پیاده‌سازی می‌کند.
# اکنون تنظیمات را از فایل config.txt می‌خواند و خروجی را در یک فایل مشخص می‌نویسد.
# این نسخه در صورت بروز مشکل در واکشی یک URL، به URL بعدی می‌رود و فرایند را متوقف نمی‌کند.
# همچنین، امکان تنظیمات جداگانه (type، count_per_url، output_file_name و detect_cloudflare) برای هر URL را فراهم می‌کند.
# پشتیبانی از count=0 برای انتخاب نامحدود.
# قابلیت جدید: شناسایی کانفیگ‌های مربوط به دامنه‌های Cloudflare Worker/Pages، با قابلیت فعال/غیرفعال‌سازی برای هر URL.
# بهبود: شناسایی Cloudflare اکنون شامل بررسی آدرس سرور اصلی، پارامترهای 'sni' و 'host' و همچنین تجزیه کانفیگ‌های Base64 (مانند VMess و برخی SS) می‌شود.
# رفع مشکل: بهبود تجزیه پارامترهای URL برای مدیریت 'amp;' در 'sni' و 'host'.
# رفع مشکل: اصلاح منطق رمزگشایی Base64 برای فایل‌های حاوی لیست کانفیگ‌ها (مانند SS و VMess).
# رفع مشکل: بازگرداندن منطق رمزگشایی Base64 برای کل محتوای واکشی شده در تابع run().
# تغییر جدید: اگر detect_cloudflare فعال باشد، فقط کانفیگ‌های Cloudflare در فایل خروجی ذخیره می‌شوند.
# قابلیت جدید: تولید فایل README.md با لینک به فایل‌های خروجی Raw در GitHub.

import base64    # برای کدگذاری و رمزگشایی Base64
import os        # برای کار با مسیرها و سیستم فایل
import random    # برای به‌هم‌ریختن آرایه
import sys       # برای خروج از اسکریپت در صورت خطا
import requests  # برای واکشی URLها (نیاز به نصب: pip install requests)
import json      # برای کار با فرمت JSON در کانفیگ‌های VMess و SS
from urllib.parse import urlparse, parse_qs, unquote # برای تجزیه URL و ساخت نام فایل پیش‌فرض و تجزیه کوئری استرینگ و رمزگشایی URL

# تابع کمکی: بررسی می‌کند که آیا یک رشته Base64 معتبر است یا خیر
def is_base64(s):
    s = s.strip()
    if not s:
        return False
    try:
        missing_padding = len(s) % 4
        if missing_padding != 0:
            s += '='* (4 - missing_padding)
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False

# تابع کمکی: یک رشته UTF-8 را به Base64 کدگذاری می‌کند
def encode_base64(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')

# تابع کمکی: یک رشته Base64 را به UTF-8 رمزگشایی می‌کند
def decode_base64(s):
    missing_padding = len(s) % 4
    if missing_padding != 0:
        s += '=' * (4 - missing_padding)
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
                                elif key.strip() == 'output_file_name':
                                    url_config['output_file_name'] = value.strip()
                                elif key.strip() == 'detect_cloudflare': # پارامتر جدید
                                    url_config['detect_cloudflare'] = value.strip().lower() == 'true'
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

# تابع جدید: شناسایی کانفیگ‌های مربوط به دامنه‌های Cloudflare Worker/Pages
def identify_cloudflare_domains(config_lines):
    cloudflare_domains = [".workers.dev", ".pages.dev"]
    identified_configs = []

    for line in config_lines:
        try:
            # قبل از تجزیه URL، کاراکترهای خاص HTML مانند '&amp;' را به '&' تبدیل می‌کنیم
            # و همچنین URL-decode می‌کنیم تا مقادیر به درستی خوانده شوند.
            processed_line = unquote(line.replace('&amp;', '&'))
            
            # حالا خط را به عنوان یک URL تجزیه می‌کنیم
            parsed_url = urlparse(processed_line)
            scheme = parsed_url.scheme.lower()
            
            # لیست دامنه‌هایی که باید بررسی شوند
            domains_to_check = []

            # 1. بررسی آدرس سرور اصلی (netloc)
            netloc = parsed_url.netloc
            if ':' in netloc:
                domain_from_netloc = netloc.split(':')[0]
            else:
                domain_from_netloc = netloc
            if domain_from_netloc:
                domains_to_check.append(domain_from_netloc)

            # 2. بررسی پارامترهای 'sni' و 'host' در رشته کوئری
            query_params = parse_qs(parsed_url.query)
            if 'sni' in query_params:
                domains_to_check.extend(query_params['sni'])
            if 'host' in query_params:
                domains_to_check.extend(query_params['host'])

            # 3. مدیریت پروتکل‌های Base64 (VMess, برخی SS)
            # این بخش برای کانفیگ‌هایی است که خودشان Base64 هستند (مثلاً بعد از vmess://)
            if scheme in ['vmess', 'ss']:
                # قسمت بعد از پروتکل (مثلاً بعد از vmess://)
                encoded_part_of_config = processed_line.split('://', 1)[-1]
                # حذف قسمت #remarks اگر وجود دارد
                if '#' in encoded_part_of_config:
                    encoded_part_of_config = encoded_part_of_config.split('#', 1)[0]
                
                # بررسی می‌کنیم که آیا این قسمت Base64 معتبر است یا خیر
                if is_base64(encoded_part_of_config):
                    try:
                        decoded_json_str = decode_base64(encoded_part_of_config)
                        config_data = json.loads(decoded_json_str)
                        
                        # برای VMess: 'add' (address), 'host', 'sni'
                        if scheme == 'vmess':
                            if 'add' in config_data:
                                domains_to_check.append(config_data['add'])
                            if 'host' in config_data:
                                domains_to_check.append(config_data['host'])
                            if 'sni' in config_data:
                                domains_to_check.append(config_data['sni'])
                        
                        # برای SS: معمولاً 'server' (اگرچه SS کمتر JSON استفاده می‌کند)
                        elif scheme == 'ss':
                            if 'server' in config_data:
                                domains_to_check.append(config_data['server'])
                            # برخی SS client ها ممکن است host یا sni را در JSON داشته باشند
                            if 'host' in config_data:
                                domains_to_check.append(config_data['host'])
                            if 'sni' in config_data:
                                domains_to_check.append(config_data['sni'])

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # اگر Base64 بود اما JSON معتبر نبود، یا رمزگشایی مشکل داشت، نادیده بگیرید
                        pass
                
            # بررسی نهایی دامنه‌های جمع‌آوری شده
            for domain in domains_to_check:
                # اطمینان از اینکه دامنه فقط شامل بخش دامنه و بدون پورت است
                if ':' in domain:
                    domain = domain.split(':')[0]
                
                if any(domain.lower().endswith(cf_domain) for cf_domain in cloudflare_domains):
                    identified_configs.append(line)
                    break # اگر یک دامنه Cloudflare پیدا شد، به خط بعدی بروید

        except Exception as e:
            # در صورت بروز خطا در تجزیه یک خط، آن را نادیده بگیرید و به خط بعدی بروید
            # print(f"خطا در پردازش خط برای شناسایی Cloudflare: {line} - {e}", file=sys.stderr)
            continue
    return identified_configs

# تابع جدید: تولید فایل README.md با لینک به فایل‌های خروجی Raw در GitHub
def generate_readme(output_folder, generated_files):
    readme_content = "# Generated Subscription Configs\n\n"
    readme_content += "This README lists the generated subscription configuration files.\n\n"

    # Get GitHub repository details from environment variables
    # These are available when running in GitHub Actions
    repo_owner = os.getenv('GITHUB_REPOSITORY_OWNER') # e.g., 'your-username'
    repo_name_full = os.getenv('GITHUB_REPOSITORY') # e.g., 'your-username/your-repo-name'
    repo_name = repo_name_full.split('/')[-1] if repo_name_full else 'your-repo-name'
    branch_name = os.getenv('GITHUB_REF_NAME', 'main') # e.g., 'main' or 'master'

    if not repo_owner:
        print("هشدار: متغیر محیطی GITHUB_REPOSITORY_OWNER یافت نشد. از نام کاربری پیش‌فرض استفاده می‌شود.", file=sys.stderr)
        repo_owner = "your-github-username" # Fallback for local testing

    if not generated_files:
        readme_content += "No configuration files were generated in this run.\n"
    else:
        readme_content += "## Available Configs\n\n"
        for file_name in generated_files:
            # Construct the raw GitHub URL
            # Example: https://raw.githubusercontent.com/username/repo/main/shuffled_outputs/file.txt
            raw_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch_name}/{output_folder}/{file_name}"
            # Remove .txt extension for the link text
            link_text = file_name.replace('.txt', '')
            readme_content += f"- [{link_text}]({raw_url})\n"

    readme_file_path = os.path.join(os.getcwd(), 'README.md')
    with open(readme_file_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"\nREADME.md generated at: {readme_file_path}")

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
        default_output_file_name = config.get('OUTPUT_FILE_NAME', 'combined_shuffled_configs.txt')
        target_urls_configs = config.get('targetUrls', [])

        print(f"تعداد پیش‌فرض (اگر برای URL مشخص نشود): {'نامحدود' if global_count == 0 else global_count}")
        if global_type_param:
            print(f"فیلتر نوع پیش‌فرض (اگر برای URL مشخص نشود): {global_type_param}")
        print(f"فایل‌های خروجی در پوشه: {output_folder}")

        if not target_urls_configs:
            print("خطا: لیست 'targetUrls' در config.txt خالی است یا وجود ندارد.", file=sys.stderr)
            sys.exit(1)

        # ایجاد پوشه خروجی اگر وجود ندارد
        full_output_path = os.path.join(os.getcwd(), output_folder)
        os.makedirs(full_output_path, exist_ok=True)
        print(f"پوشه خروجی ایجاد شد: {full_output_path}")

        # لیست برای ذخیره نام فایل‌های خروجی که با موفقیت تولید شده‌اند
        successfully_generated_files = []

        for url_config in target_urls_configs:
            current_url = url_config.get('url')
            if not current_url:
                print(f"هشدار: یک شیء URL در config.txt فاقد 'url' است. نادیده گرفته شد.", file=sys.stderr)
                continue

            # استفاده از تنظیمات خاص URL، در غیر این صورت از تنظیمات سراسری استفاده می‌کند
            current_type_param = url_config.get('type', global_type_param)
            current_count_per_url = url_config.get('count_per_url', global_count) # پیش‌فرض از global_count
            current_output_file_name = url_config.get('output_file_name')
            detect_cloudflare_for_url = url_config.get('detect_cloudflare', False) # مقدار پیش‌فرض False

            # اگر output_file_name برای این URL مشخص نشده باشد، یک نام پیش‌فرض تولید می‌کند
            if not current_output_file_name:
                parsed_url = urlparse(current_url)
                # استفاده از نام دامنه و بخشی از مسیر برای نام فایل
                domain_name = parsed_url.netloc.replace('.', '_').replace('-', '_')
                path_hash = str(abs(hash(parsed_url.path)))[:8] # هش بخشی از مسیر برای منحصر به فرد بودن
                current_output_file_name = f"{domain_name}_{path_hash}_configs.txt"
                print(f"  نام فایل خروجی پیش‌فرض برای '{current_url}': {current_output_file_name}")

            print(f"\nدر حال پردازش URL: {current_url}")
            if current_type_param:
                print(f"  فیلتر نوع خاص برای این URL: {current_type_param}")
            print(f"  تعداد خطوط برای انتخاب از این URL: {'نامحدود' if current_count_per_url == 0 else current_count_per_url}")
            print(f"  فایل خروجی این URL: {current_output_file_name}")
            print(f"  شناسایی Cloudflare برای این URL: {'فعال' if detect_cloudflare_for_url else 'غیرفعال'}")


            try:
                # واکشی محتوا از URL مقصد
                response = requests.get(current_url, timeout=10)
                response.raise_for_status()

                text = response.text
                print(f"  طول محتوای واکشی شده: {len(text)}")

                # بازگرداندن منطق رمزگشایی Base64 برای کل محتوا
                if is_base64(text.strip()):
                    print('  محتوا به عنوان Base64 شناسایی شد، در حال رمزگشایی...')
                    try:
                        text = decode_base64(text.strip())
                        print(f"  طول محتوای رمزگشایی شده: {len(text)}")
                    except Exception as e:
                        print(f"  خطا در رمزگشایی Base64 محتوای کامل: {e}", file=sys.stderr)
                        text = "" 

                current_lines = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('#')]
                print(f"  تعداد خطوط معتبر اولیه از این URL: {len(current_lines)}")

                if current_type_param:
                    types = [t.strip().lower() for t in current_type_param.split(',')]
                    current_lines = [line for line in current_lines if any(line.lower().startswith(f"{t}://") for t in types)]
                    print(f"  تعداد خطوط پس از فیلتر نوع از این URL: {len(current_lines)}")

                # شناسایی کانفیگ‌های Cloudflare
                cloudflare_configs = []
                if detect_cloudflare_for_url:
                    cloudflare_configs = identify_cloudflare_domains(current_lines)
                    if cloudflare_configs:
                        print("\n  --- کانفیگ‌های Cloudflare شناسایی شده در این URL: ---")
                        for cf_config in cloudflare_configs:
                            print(f"    - {cf_config}")
                        print("  --------------------------------------------------")
                    else:
                        print("  هیچ کانفیگ Cloudflare در این URL شناسایی نشد.")
                else:
                    print("  شناسایی Cloudflare برای این URL غیرفعال است.")


                shuffle_array(current_lines) # به‌هم‌ریختن خطوط این URL

                # انتخاب خطوط برای ذخیره بر اساس detect_cloudflare_for_url
                if detect_cloudflare_for_url:
                    selected_lines = cloudflare_configs
                    print(f"  تعداد {len(selected_lines)} خط Cloudflare برای این URL انتخاب شد.")
                else:
                    if current_count_per_url == 0:
                        selected_lines = current_lines
                    else:
                        selected_lines = current_lines[:current_count_per_url]
                    print(f"  تعداد {len(selected_lines)} خط برای این URL انتخاب شد.")

                # فقط در صورتی فایل را ذخیره کن که خطوطی برای ذخیره وجود داشته باشد
                if selected_lines:
                    # اتصال خطوط انتخاب شده و کدگذاری نهایی به Base64
                    final_text = "\r\n".join(selected_lines)
                    base64_data = encode_base64(final_text)

                    # نوشتن خروجی به فایل مخصوص این URL
                    output_file_path = os.path.join(full_output_path, current_output_file_name)
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        f.write(base64_data)
                    print(f"  خروجی این URL در فایل ذخیره شد: {output_file_path}")
                    successfully_generated_files.append(current_output_file_name) # اضافه کردن نام فایل به لیست موفق‌ها
                else:
                    print(f"  هیچ خطی برای ذخیره از این URL انتخاب نشد. فایل خروجی ایجاد نشد.")


            except requests.exceptions.Timeout:
                print(f"  خطا: واکشی URL '{current_url}' به دلیل اتمام زمان متوقف شد.", file=sys.stderr)
            except requests.exceptions.RequestException as e:
                print(f"  خطا در واکشی URL '{current_url}': {e}", file=sys.stderr)
            except Exception as e:
                print(f"  خطای غیرمنتظره در پردازش URL '{current_url}': {e}", file=sys.stderr)

        # پس از پردازش تمام URLها، README را تولید کن
        generate_readme(output_folder, successfully_generated_files)

    except FileNotFoundError:
        print(f"خطا: فایل پیکربندی config.txt یافت نشد.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"اکشن با خطا مواجه شد: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()
