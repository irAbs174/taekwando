"""Seed demo data; historical Japanese examples are retained as Japanese."""
from __future__ import annotations

import datetime
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from apps.accounts.models import User, UserRole
from apps.accounts.rbac import ensure_role_groups
from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory, BeltType
from apps.blog.models import Category, CategoryTranslation, Post, PostTranslation, Tag
from apps.competitions.models import Competition, CompetitionParticipation
from apps.contact.models import ContactMessage
from apps.core.models import ApprovalStatus, Discipline, PublicationStatus
from apps.core.services import ModerationService
from apps.medals.models import Medal, MedalType
from apps.members.models import MembershipStatus
from apps.members.services import (
    create_member_profile_with_application,
    review_membership_application,
)
from apps.pages.models import Page, PageTranslation, PageType
from apps.products.models import (
    Product,
    ProductCategory,
    ProductCategoryTranslation,
    ProductImage,
    ProductTranslation,
)
from apps.seo.models import RouteKey, SEOMetadata, SEOTranslation


def _make_card_png(bg_hex: str, accent_hex: str, size=(640, 420)) -> ContentFile:
    """Create a branded editorial placeholder (no external assets required)."""
    img = Image.new("RGB", size, bg_hex)
    draw = ImageDraw.Draw(img)
    w, h = size
    # Soft oversized rings and a diagonal accent give the card depth without photos.
    draw.ellipse([w - 250, -140, w + 190, 300], outline="#ffffff", width=2)
    draw.ellipse([-160, h - 170, 260, h + 250], outline="#ffffff", width=2)
    draw.polygon([(w - 150, 0), (w, 0), (w, 150)], fill=accent_hex)
    draw.rectangle([0, h - 12, w, h], fill=accent_hex)

    # Brand emblem: ring, monogram T, belt line and knot.
    cx, cy, r = w // 2, h // 2 - 26, 66
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#ffffff", width=4)
    draw.rectangle([cx - 30, cy - 26, cx + 30, cy - 10], fill="#ffffff")
    draw.rectangle([cx - 10, cy - 26, cx + 10, cy + 26], fill="#ffffff")
    draw.rectangle([cx - 30, cy + 4, cx + 30, cy + 16], fill=accent_hex)
    draw.ellipse([cx - 5, cy + 5, cx + 5, cy + 15], fill="#f2c14e")

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        wordmark = ImageFont.truetype(font_path, 30)
        caption = ImageFont.truetype(font_path, 13)
    except OSError:  # pragma: no cover - depends on host fonts
        wordmark = ImageFont.load_default()
        caption = ImageFont.load_default()
    title = "TECHWANDO"
    box = draw.textbbox((0, 0), title, font=wordmark)
    draw.text(((w - (box[2] - box[0])) / 2, cy + r + 26), title, fill="#ffffff", font=wordmark)
    subtitle = "MARTIAL ARTS CLUB"
    box = draw.textbbox((0, 0), subtitle, font=caption)
    draw.text(
        ((w - (box[2] - box[0])) / 2, cy + r + 64),
        subtitle,
        fill="#ffffff",
        font=caption,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name="visual.png")


class Command(BaseCommand):
    help = "Populate TECHWANDO with demo belt ranks, pages, blog, products, and athletes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-demo-accounts",
            action="store_true",
            help="Also create demo staff and champion member accounts for local testing.",
        )
        parser.add_argument(
            "--demo-password",
            default="Techwando!2026",
            help="Password for demo accounts (local development only).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_role_groups()
        self._seed_belts()
        comps = self._seed_competitions()
        self._seed_pages()
        self._seed_seo()
        author = None
        if options["with_demo_accounts"]:
            author = self._seed_accounts_and_athletes(comps, options["demo_password"])
        self._seed_blog(author)
        self._seed_products()
        self.stdout.write(self.style.SUCCESS("TECHWANDO bilingual catalog & records seeded."))

    def _seed_belts(self):
        belts = [
            # Taekwondo
            (Discipline.TAEKWONDO, "10-GEUP", 1, "کمربند سفید (گوپ ۱۰)", "白帯（10級）", "#e5e7eb", False),
            (Discipline.TAEKWONDO, "8-GEUP", 2, "کمربند زرد (گوپ ۸)", "黄帯（8級）", "#eab308", False),
            (Discipline.TAEKWONDO, "6-GEUP", 3, "کمربند سبز (گوپ ۶)", "緑帯（6級）", "#16a34a", False),
            (Discipline.TAEKWONDO, "4-GEUP", 4, "کمربند آبی (گوپ ۴)", "青帯（4級）", "#2563eb", False),
            (Discipline.TAEKWONDO, "2-GEUP", 5, "کمربند قرمز (گوپ ۲)", "赤帯（2級）", "#dc2626", False),
            (Discipline.TAEKWONDO, "1-DAN", 10, "کمربند مشکی دان ۱", "黒帯 初段", "#111827", True),
            (Discipline.TAEKWONDO, "2-DAN", 11, "کمربند مشکی دان ۲", "黒帯 二段", "#111827", True),
            (Discipline.TAEKWONDO, "3-DAN", 12, "کمربند مشکی دان ۳", "黒帯 三段", "#111827", True),
            (Discipline.TAEKWONDO, "4-DAN", 13, "کمربند مشکی دان ۴ (استادی)", "黒帯 四段（師範）", "#0f172a", True),
            # Karate
            (Discipline.KARATE, "6-KYU", 1, "کمربند سبز کاراته (کیو ۶)", "空手 緑帯（6級）", "#15803d", False),
            (Discipline.KARATE, "1-KYU", 5, "کمربند قهوه‌ای کاراته (کیو ۱)", "空手 茶帯（1級）", "#78350f", False),
            (Discipline.KARATE, "1-DAN", 10, "کمربند مشکی کاراته دان ۱", "空手 黒帯 初段", "#111827", True),
            (Discipline.KARATE, "2-DAN", 11, "کمربند مشکی کاراته دان ۲", "空手 黒帯 二段", "#111827", True),
            # Judo
            (Discipline.JUDO, "1-KYU", 5, "کمربند قهوه‌ای جودو (کیو ۱)", "柔道 茶帯（1級）", "#78350f", False),
            (Discipline.JUDO, "1-DAN", 10, "کمربند مشکی جودو دان ۱", "柔道 黒帯 初段", "#111827", True),
            (Discipline.JUDO, "2-DAN", 11, "کمربند مشکی جودو دان ۲", "柔道 黒帯 二段", "#111827", True),
        ]
        for disc, code, order, fa, ja, color, is_black in belts:
            BeltType.objects.update_or_create(
                discipline=disc,
                rank_code=code,
                defaults={
                    "rank_order": order,
                    "name_fa": fa,
                    "name_ja": ja,
                    "color_hex": color,
                    "is_black_belt": is_black,
                    "is_active": True,
                },
            )

    def _seed_competitions(self) -> list[Competition]:
        specs = [
            {
                "slug": "tokyo-international-taekwondo-open-2026",
                "discipline": Discipline.TAEKWONDO,
                "title_fa": "مسابقات بین‌المللی اوپن تکواندو توکیو ۲۰۲۶",
                "title_ja": "2026年 東京国際テコンドーオープン選手権大会",
                "location_fa": "توکیو، ژاپن — ورزشگاه ملی یویوگی",
                "location_ja": "東京都・国立代々木競技場",
                "start_date": datetime.date(2026, 5, 14),
                "end_date": datetime.date(2026, 5, 17),
                "organizer": "فدراسیون بین‌المللی تکواندو شرق آسیا",
                "organizer_ja": "東アジア国際テコンドー連盟",
                "description_fa": "رقابت‌های رسمی کیوروگی و پومسه با حضور ورزشکاران برتر باشگاه‌های آسیایی.",
                "description_ja": "アジア各国の公認クラブ代表選手が集うキョルギ・プムセ公式国際大会。",
                "results_summary_fa": "تیم باشگاه تکواندو موفق به کسب ۲ مدال طلا و ۱ مدال نقره در رده بزرگسالان شد.",
                "results_summary_ja": "TECHWANDO代表チームはシニア部門で金メダル2個・銀メダル1個を獲得しました。",
            },
            {
                "slug": "tehran-friendship-budo-cup-2026",
                "discipline": Discipline.KARATE,
                "title_fa": "جام دوستی هنرهای رزمی تهران — کیوتو ۲۰۲۶",
                "title_ja": "2026年 テヘラン・京都友好武道選手権大会",
                "location_fa": "تهران، ایران — تالار فدراسیون هنرهای رزمی",
                "location_ja": "イラン・テヘラン 武道連盟アリーナ",
                "start_date": datetime.date(2026, 3, 8),
                "end_date": datetime.date(2026, 3, 10),
                "organizer": "انجمن مشترک فرهنگی ورزشی ایران و ژاپن",
                "organizer_ja": "日本・イラン武道文化交流協会",
                "description_fa": "رویداد مشترک تبادل فنی و مسابقات رسمی کاتا، کومیته و پومسه.",
                "description_ja": "形・組手・プムセの公式競技および合同技術講習会を兼ねた友好大会。",
                "results_summary_fa": "درخشش ورزشکاران جوان آکادمی در بخش کاتا انفرادی و تیمی.",
                "results_summary_ja": "個人形・団体形部門でアカデミー所属選手が優秀な成績を収めました。",
            },
            {
                "slug": "osaka-all-japan-judo-invitational-2025",
                "discipline": Discipline.JUDO,
                "title_fa": "مسابقات دعوتی جودو و دفاع شخصی اوساکا ۲۰۲۵",
                "title_ja": "2025年 大阪選抜柔道・武道招待大会",
                "location_fa": "اوساکا، ژاپن — سالن مرکزی بودوکان",
                "location_ja": "大阪府立武道館",
                "start_date": datetime.date(2025, 11, 2),
                "end_date": datetime.date(2025, 11, 3),
                "organizer": "کمیته برگزاری مسابقات اوساکا",
                "organizer_ja": "大阪武道大会実行委員会",
                "description_fa": "مسابقات سالانه با حضور باشگاه‌های منتخب رشته‌های جودو و تکواندو.",
                "description_ja": "選抜クラブによる柔道・総合武道の年次公式招待大会。",
                "results_summary_fa": "کسب مدال برنز وزن منفی ۷۳ کیلوگرم و جایزه اخلاق ورزشی.",
                "results_summary_ja": "男子73kg級銅メダルおよび敢闘・礼節賞を受賞。",
            },
        ]
        result = []
        for s in specs:
            slug = s.pop("slug")
            comp, _ = Competition.objects.update_or_create(
                slug=slug, defaults={**s, "is_published": True}
            )
            result.append(comp)
        return result

    def _seed_pages(self):
        pages = [
            {
                "slug": "about",
                "page_type": PageType.ABOUT,
                "order": 1,
                "footer": True,
                "fa": (
                    "درباره آکادمی و باشگاه تکواندو (TECHWANDO)",
                    "پیوند انضباط سنتی هنرهای رزمی با دانش نوین علوم ورزشی",
                    "آکادمی تکواندو بستری حرفه‌ای و دوزبانه برای آموزش هنرهای رزمی، پرورش قهرمانان، ثبت رسمی کمربندها و مستندسازی افتخارات ورزشی بین جوامع فارسی‌زبان و کره‌ای‌زبان است.",
                    "باشگاه تکواندو (TECHWANDO) با هدف ارتقای استاندارد آموزش هنرهای رزمی، اخلاق پهلوانی و شفافیت در ثبت سوابق ورزشی بنیان‌گذاری شده است.\n\n"
                    "در این مجموعه، هر هنرجو از نخستین روز ورود دارای پرونده ورزشی اختصاصی است و تمامی مراحل ارتقای کمربند، حضور در مسابقات، مدال‌های کسب‌شده و فعالیت‌های فرهنگی‌اجتماعی پس از بررسی مستندات توسط هیئت فنی و مدیران باشگاه تأیید و ثبت می‌گردد.\n\n"
                    "ارزش‌های بنیادین ما بر احترام متقابل (ادب و ریگی)، پشتکار پیوسته، سلامت جسم و ذهن، و مسئولیت‌پذیری اجتماعی استوار است.",
                ),
                "ja": (
                    "TECHWANDO（テクワンドー）について",
                    "伝統武道の礼節と現代スポーツ科学を融合した国際武道アカデミー",
                    "TECHWANDOは、武道教育・クラブ運営・公認選手プロフィール・昇級昇段・メダル実績を一元管理するペルシャ語・日本語対応の公式プラットフォームです。",
                    "TECHWANDO（テクワンドー）は、礼節（礼に始まり礼に終わる精神）、技術向上、そして公正な競技実績の認証を目的に設立された武道・スポーツ教育クラブです。\n\n"
                    "すべてのクラブ会員には専用ポータルが付与され、昇級・昇段審査の履歴、公式大会への出場記録、獲得メダル、地域社会貢献活動が証明書とともに厳正な審査ワークフローを経て公認記録として登録されます。\n\n"
                    "イランと日本をつなぐ武道交流の架け橋として、青少年育成から国際大会を目指すトップアスリートまで体系的な指導を提供しています。",
                ),
            },
            {
                "slug": "poomsae-and-kata-curriculum",
                "page_type": PageType.EDUCATION,
                "order": 1,
                "footer": False,
                "fa": (
                    "سرفصل جامع آموزش پومسه و کاتا",
                    "از فرم‌های پایه تگوک تا فرم‌های پیشرفته کمربند مشکی",
                    "آموزش گام‌به‌گام تعادل، تنفس، ریتم اجرای تکنیک و دقت زاویه‌ها برای آزمون‌های رسمی ارتقای کمربند.",
                    "این دوره آموزشی شامل تحلیل دقیق فرم‌های تگوک (۱ تا ۸) و فرم‌های دان مشکی (کوریو، کومگانگ، ته‌بک) به همراه اصول بنیادین کاتا است.\n\n"
                    "هنرجویان با معیارهای داوری بین‌المللی، کنترل مرکز ثقل، هماهنگی تنفس با ضربات و تمرکز ذهنی آشنا می‌شوند.",
                ),
                "ja": (
                    "プムセ・形（カタ）体系カリキュラム",
                    "太極（テグク）基本型から黒帯高段者向け演武まで",
                    "重心移動・呼吸法・正確な角度と緩急を段階的に習得し、公式昇級・昇段審査に備えます。",
                    "本カリキュラムでは、太極1章〜8章から高麗（コリョ）・金剛（クムガン）・太白（テベク）などの有段者プムセ、および空手の基本形を体系的に学びます。\n\n"
                    "国際審判基準に基づいた姿勢制御、正確な技の軌道、気迫と礼法を実践的に指導します。",
                ),
            },
            {
                "slug": "sports-science-and-injury-prevention",
                "page_type": PageType.EDUCATION,
                "order": 2,
                "footer": False,
                "fa": (
                    "فیزیولوژی ورزشی، آمادگی جسمانی و پیشگیری از آسیب",
                    "طراحی تمرین علمی برای رزمی‌کاران حرفه‌ای و نوجوانان",
                    "اصول گرم‌کردن پویا، انعطاف‌پذیری لگن و همسترینگ، تغذیه پیش از وزن‌کشی و ریکاوری علمی.",
                    "موفقیت پایدار در هنرهای رزمی نیازمند شناخت علمی بدن است. در این بخش آموزشی، پروتکل‌های استاندارد پیشگیری از آسیب زانو و مچ پا، تمرینات پلایومتریک ویژه ضربات پا و مدیریت انرژی در سه راند مسابقه آموزش داده می‌شود.",
                ),
                "ja": (
                    "スポーツ医科学・フィジカル強化と傷害予防",
                    "武道競技者のための科学的コンディショニング",
                    "動的ウォームアップ、股関節の柔軟性向上、計量前後の栄養管理、疲労回復プロトコルを解説。",
                    "長く高い競技力を維持するためには科学的な身体づくりが不可欠です。膝・足関節の傷害予防プログラム、蹴り技の瞬発力を高めるプライオメトリクス、試合3ラウンドを戦い抜く心肺持久力トレーニングを学びます。",
                ),
            },
            {
                "slug": "budo-etiquette-and-ethics",
                "page_type": PageType.EDUCATION,
                "order": 3,
                "footer": False,
                "fa": (
                    "آیین دوجانگ، اخلاق رزمی و رهبری اجتماعی",
                    "پرورش شخصیت، احترام به استاد و مسئولیت‌پذیری در جامعه",
                    "آشنایی با منشور اخلاقی باشگاه، آداب حضور در دوجانگ و نقش ورزشکاران در فعالیت‌های داوطلبانه.",
                    "هنر رزمی تنها مهارت مبارزه نیست؛ بلکه مکتب انسان‌سازی است. در تکواندو، فعالیت‌های اجتماعی و داوطلبانه اعضا بخش مهمی از مسیر رشد و ارتقای درجات ارشد محسوب می‌شود.",
                ),
                "ja": (
                    "道場訓・礼法（礼儀）と社会貢献リーダーシップ",
                    "心技体の調和と地域社会に信頼される武道家の育成",
                    "道場での礼法、師範・仲間への敬意、そして青少年指導や地域ボランティア活動の意義を学びます。",
                    "武道の本質は勝敗を超えた人格形成にあります。TECHWANDOでは、競技成績だけでなく地域清掃・青少年スポーツ教室・国際交流などの社会活動を奨励し、公式実績として評価しています。",
                ),
            },
            {
                "slug": "kyorugi-championship-squad",
                "page_type": PageType.SERVICE,
                "order": 1,
                "footer": False,
                "fa": (
                    "تیم قهرمانی و مبارزه مسابقاتی (کیوروگی)",
                    "تمرینات تخصصی با هوگو الکترونیکی و آنالیز ویدئویی",
                    "ویژه ورزشکاران کمربند آبی به بالا با هدف آمادگی برای مسابقات ملی و بین‌المللی.",
                    "برنامه تمرینی تیم قهرمانی شامل ۵ جلسه تمرین تخصصی در هفته، شبیه‌سازی مسابقات با سیستم امتیازدهی الکترونیکی، تمرینات تاکتیکی و همراهی مربیان رسمی در رویدادهای بین‌المللی است.",
                ),
                "ja": (
                    "キョルギ（組手）選手強化コース",
                    "電子防具システムと映像分析を導入した実戦トレーニング",
                    "国内・国際大会出場を目指す中上級者・有段者向けの専門強化プログラム（週5回）。",
                    "最新の電子防具（PSS）を用いた実戦形式スパーリング、戦術分析、個別フィジカルメニューにより、国際舞台で戦える競技力を養成します。",
                ),
            },
            {
                "slug": "youth-foundations-program",
                "page_type": PageType.SERVICE,
                "order": 2,
                "footer": False,
                "fa": (
                    "آکادمی پایه کودکان و نوجوانان (۶ تا ۱۵ سال)",
                    "افزایش اعتمادبه‌نفس، تمرکز، هماهنگی حرکتی و نظم فردی",
                    "محیطی ایمن، شاداب و استاندارد زیر نظر مربیان دارای گواهینامه بین‌المللی استعدادیابی.",
                    "کلاس‌های رده سنی پایه در گروه‌های هم‌سطح برگزار می‌شود و بر مهارت‌های بنیادی حرکتی، انعطاف‌پذیری، احترام به والدین و مربیان و آزمون‌های دوره‌ای کمربند تمرکز دارد.",
                ),
                "ja": (
                    "ジュニア武道育成クラス（6歳〜15歳）",
                    "礼儀作法・集中力・基礎運動能力を楽しく伸ばす安心の指導環境",
                    "年齢・帯レベル別の少人数制クラスで、初めての子どもでも無理なく基礎から学べます。",
                    "公認指導員のもと、安全なマット環境で基本動作・柔軟性・協調性・挨拶の習慣を育み、定期昇級審査を通じて達成感を積み重ねます。",
                ),
            },
            {
                "slug": "dan-promotion-academy",
                "page_type": PageType.SERVICE,
                "order": 3,
                "footer": False,
                "fa": (
                    "دوره آمادگی آزمون دان مشکی و مربیگری",
                    "بازآموزی تخصصی تکنیک‌ها، دفاع شخصی (هوسین‌سول) و شکستن اجسام (کیوکپا)",
                    "همراه با ثبت و تأیید رسمی گواهینامه ارتقای کمربند در سامانه جامع باشگاه.",
                    "داوطلبان ارتقای کمربند مشکی دان ۱ تا دان ۴ تحت نظر اساتید ارشد برای آزمون‌های رسمی فدراسیونی آماده می‌شوند و پس از قبولی، سابقه رسمی آنان در پورتال و فهرست افتخارات ثبت می‌گردد.",
                ),
                "ja": (
                    "黒帯昇段・指導員養成プログラム",
                    "高段者プムセ・護身術（ホシンスル）・試割（キョクパ）の徹底指導",
                    "初段〜四段の公式昇段審査対策およびクラブ公認指導員資格の取得を支援します。",
                    "師範陣による直接指導で技術精度と指導法を磨き、合格後は証明書審査を経て公式黒帯レジストリに認定登録されます。",
                ),
            },
            {
                "slug": "terms-of-service",
                "page_type": PageType.LEGAL,
                "order": 11,
                "footer": True,
                "fa": (
                    "شرایط استفاده و آیین‌نامه عضویت در باشگاه",
                    "قواعد استفاده از سامانه، رفتار ورزشی و مسئولیت اعضا",
                    "استفاده از وب‌سایت و پرتال اعضا به معنای پذیرش شرایط باشگاه، آیین‌نامه اخلاقی و قوانین دوجانگ است.",
                    "عضویت در باشگاه پس از بررسی درخواست و تأیید مدیران انجام می‌شود. هر عضو تنها به اطلاعات خصوصی و سوابق ورزشی خود دسترسی دارد.\n\n"
                    "ثبت افتخارات، مدال‌ها، ارتقای کمربند، مسابقات و فعالیت‌های اجتماعی نیازمند ارائه مستندات و تأیید هیئت فنی است و عضو نمی‌تواند وضعیت بررسی یا تصمیم مدیران را تغییر دهد.\n\n"
                    "فروشگاه تجهیزات صرفاً جنبه معرفی دارد و هیچ پرداخت آنلاینی در سامانه انجام نمی‌شود. رعایت اصول ایمنی، احترام متقابل و پرهیز از انتشار اطلاعات خصوصی دیگران الزامی است.",
                ),
                "ja": (
                    "利用規約・会員規程",
                    "本サイトおよび会員ポータルのご利用条件",
                    "本ウェブサイトおよび会員ポータルの利用をもって、クラブ規約・道場訓・行動規範に同意したものとみなします。",
                    "会員登録は管理者による審査・承認後に有効となります。各会員は自身の非公開情報および競技記録のみにアクセスできます。\n\n"
                    "実績・メダル・昇段・大会参加・社会活動の登録には証明書類の提出と技術委員会の承認が必要であり、会員が自ら審査結果を変更することはできません。\n\n"
                    "用品カタログは情報提供のみを目的とし、オンライン決済機能は提供していません。安全指導の遵守、相互尊重、他者の個人情報の保護を必須とします。",
                ),
            },
            {
                "slug": "privacy-policy",
                "page_type": PageType.LEGAL,
                "order": 10,
                "footer": True,
                "fa": (
                    "حریم خصوصی و حفاظت از اطلاعات ورزشکاران",
                    "شفافیت کامل در نگهداری مدارک و نمایش عمومی پروفایل قهرمانان",
                    "اطلاعات تماس، تاریخ تولد و فایل گواهینامه‌های اعضا کاملاً محرمانه است و هرگز به‌صورت عمومی منتشر نمی‌شود.",
                    "در سامانه تکواندو، نمایش پروفایل ورزشی در بخش قهرمانان تنها در صورت تأیید مدیر باشگاه و اعلام رضایت صریح عضو انجام می‌گیرد. فایل گواهینامه‌ها و مدارک در فضای ذخیره‌سازی خصوصی نگهداری شده و صرفاً برای خود عضو و بازرسان مجاز قابل مشاهده است.",
                ),
                "ja": (
                    "プライバシーポリシー・個人情報保護方針",
                    "会員データおよび証明書類の厳格なアクセス管理について",
                    "連絡先・生年月日・証明書ファイルは非公開領域で保護され、一般公開されることは一切ありません。",
                    "TECHWANDOでは、会員本人の明示的な公開同意と管理者の承認が揃った競技実績のみをチャンピオンページに掲載します。アップロードされた証明書・メダル証憑は非公開ストレージに保管され、本人および権限を持つ審査担当者のみが閲覧できます。",
                ),
            },
        ]
        for item in pages:
            page, _ = Page.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "page_type": item["page_type"],
                    "status": PublicationStatus.PUBLISHED,
                    "display_order": item["order"],
                    "show_in_footer": item["footer"],
                },
            )
            for code in ("fa", "ja"):
                title, subtitle, summary, body = item[code]
                PageTranslation.objects.update_or_create(
                    page=page,
                    language=code,
                    defaults={
                        "title": title,
                        "subtitle": subtitle,
                        "summary": summary,
                        "body": body,
                        "seo_title": title,
                        "seo_description": summary[:300],
                    },
                )

    def _seed_seo(self):
        entries = [
            (
                RouteKey.HOME,
                "آکادمی هنرهای رزمی و باشگاه تکواندو | TECHWANDO",
                "پلتفرم دوزبانه آموزش تکواندو و هنرهای رزمی، مدیریت باشگاه، پروفایل رسمی قهرمانان و ثبت مدال‌ها.",
                "TECHWANDO（テクワンドー）公式｜武道教育・クラブ管理・公認選手プラットフォーム",
                "テコンドー・空手・柔道の体系的教育、会員ポータル、公認チャンピオン実績・メダル管理を行う国際武道クラブ。",
            ),
            (
                RouteKey.CHAMPIONS,
                "فهرست قهرمانان و ورزشکاران رسمی | TECHWANDO",
                "جستجو و مشاهده پروفایل رسمی قهرمانان، دارندگان کمربند مشکی و مدال‌آوران تأییدشده باشگاه تکواندو.",
                "公認チャンピオン・選手名鑑｜TECHWANDO",
                "厳正な審査を経て認定されたTECHWANDO所属アスリート・黒帯有段者・メダリストの公式ディレクトリ。",
            ),
            (
                RouteKey.BLOG,
                "مجله تخصصی و مقالات آموزشی هنرهای رزمی | TECHWANDO",
                "مقالات فنی تکواندو، کاراته، جودو، آمادگی جسمانی و اخبار مسابقات به زبان‌های فارسی و کره‌ای.",
                "武道コラム・技術ブログ｜TECHWANDO",
                "テコンドー・武道の技術解説、試合レポート、スポーツ科学に関する最新記事を日本語・ペルシャ語で発信。",
            ),
            (
                RouteKey.PRODUCTS,
                "تجهیزات و پوشاک استاندارد هنرهای رزمی | TECHWANDO",
                "کاتالوگ رسمی لباس دوبوک و دوگی، محافظ‌های استاندارد مسابقاتی، کمربند و تجهیزات تمرینی.",
                "公認武道用品・トレーニングギア｜TECHWANDO",
                "公式道着（ドボク・道衣）、認定プロテクター、黒帯、トレーニング用品の製品カタログ。",
            ),
        ]
        for key, fa_t, fa_d, ja_t, ja_d in entries:
            seo, _ = SEOMetadata.objects.get_or_create(
                route_key=key,
                defaults={"robots_index": True, "robots_follow": True},
            )
            SEOTranslation.objects.update_or_create(
                seo=seo,
                language="fa",
                defaults={"seo_title": fa_t, "seo_description": fa_d, "og_title": fa_t, "og_description": fa_d},
            )
            SEOTranslation.objects.update_or_create(
                seo=seo,
                language="ja",
                defaults={"seo_title": ja_t, "seo_description": ja_d, "og_title": ja_t, "og_description": ja_d},
            )

    def _seed_blog(self, author):
        cat_specs = [
            ("technique", 1, "تکنیک و آموزش", "技術・トレーニング"),
            ("championships", 2, "اخبار مسابقات", "大会ニュース"),
            ("club-culture", 3, "فرهنگ و اخلاق رزمی", "武道文化・礼節"),
        ]
        cats = {}
        for slug, order, fa, ja in cat_specs:
            c, _ = Category.objects.update_or_create(
                slug=slug, defaults={"display_order": order, "is_active": True}
            )
            CategoryTranslation.objects.update_or_create(
                category=c, language="fa", defaults={"name": fa}
            )
            CategoryTranslation.objects.update_or_create(
                category=c, language="ja", defaults={"name": ja}
            )
            cats[slug] = c

        t1, _ = Tag.objects.update_or_create(
            slug="taekwondo", defaults={"name_fa": "تکواندو", "name_ja": "テコンドー"}
        )
        t2, _ = Tag.objects.update_or_create(
            slug="dan-exam", defaults={"name_fa": "آزمون دان", "name_ja": "昇段審査"}
        )
        t3, _ = Tag.objects.update_or_create(
            slug="conditioning", defaults={"name_fa": "آمادگی جسمانی", "name_ja": "コンディショニング"}
        )

        posts = [
            {
                "slug": "mastering-dollyo-chagi-biomechanics",
                "cat": cats["technique"],
                "tags": [t1, t3],
                "featured": True,
                "days_ago": 5,
                "colors": ("#0f172a", "#dc2626"),
                "fa": (
                    "اصول بیومکانیک ضربه دولیو چاگی در مبارزات مدرن",
                    "چگونه چرخش پاشنه پای تکیه‌گاه و باز شدن لگن، سرعت و دقت ضربه را دو برابر می‌کند.",
                    "ضربه دولیو چاگی یکی از امتیازآورترین تکنیک‌ها در تکواندوی مسابقاتی است. کلید اجرای بی‌نقص این ضربه در هماهنگی زنجیره حرکتی از مچ پای تکیه‌گاه تا لگن و زانو نهفته است.\n\n"
                    "۱. چرخش کامل پای تکیه‌گاه تا زاویه ۱۶۰ تا ۱۸۰ درجه برای کاهش فشار بر رباط‌های زانو.\n"
                    "۲. بالا آوردن زانو در کوتاه‌ترین مسیر خطی پیش از باز شدن ساق پا.\n"
                    "۳. بازگشت سریع پا به گارد دفاعی بلافاصله پس از برخورد با هوگو.\n\n"
                    "تمرین مداوم این سه اصل با کش‌های مقاومتی در جلسات هفتگی آکادمی تکواندو دنبال می‌شود.",
                    "اجرای تکنیک دولیو چاگی در دوجانگ تکواندو",
                ),
                "ja": (
                    "現代キョルギにおけるトルリョチャギ（回し蹴り）のバイオメカニクス",
                    "軸足の回転角度と股関節の連動が蹴り速度・正確性を飛躍的に高める理由を解説します。",
                    "トルリョチャギ（回し蹴り）はテコンドー競技において最も重要な得点技の一つです。高い打点とスピードを両立させる鍵は、足首・股関節・体幹の運動連鎖にあります。\n\n"
                    "1. 膝関節への負担を軽減し腰を完全に開くため、軸足を160〜180度スムーズに回転させる。\n"
                    "2. 膝を最短軌道で引き上げ、インパクト直前に鞭のように膝下を解放する。\n"
                    "3. 電子防具への正確なミート後、即座に引き足を取って防御姿勢へ復帰する。\n\n"
                    "TECHWANDOの技術クラスでは、レジスタンスバンドとスロー映像分析を用いて基礎から徹底指導しています。",
                    "TECHWANDO道場でのトルリョチャギ技術解説",
                ),
            },
            {
                "slug": "tokyo-open-2026-team-report",
                "cat": cats["championships"],
                "tags": [t1],
                "featured": True,
                "days_ago": 12,
                "colors": ("#1e293b", "#d97706"),
                "fa": (
                    "گزارش درخشش کاروان باشگاه تکواندو در مسابقات اوپن توکیو ۲۰۲۶",
                    "کسب دو مدال طلا و یک نقره توسط ورزشکاران تأییدشده باشگاه در رقابت‌های بین‌المللی یویوگی.",
                    "تیم منتخب باشگاه تکواندو با ترکیبی از ورزشکاران ایرانی و ژاپنی در مسابقات بین‌المللی توکیو ۲۰۲۶ حضور یافت و عملکردی درخشان از خود به جای گذاشت.\n\n"
                    "تمامی مدال‌ها و گواهینامه‌های رسمی این رویداد پس از بازبینی کمیته فنی در بخش «قهرمانان» و «برندگان مدال» سامانه منتشر شده است.",
                    "مدال‌آوران باشگاه تکواندو در اوپن توکیو",
                ),
                "ja": (
                    "2026年 東京国際オープン大会レポート：金2・銀1の快挙",
                    "国立代々木競技場で開催された国際大会にて、TECHWANDO代表選手団が素晴らしい成績を収めました。",
                    "イラン・日本両国の所属選手で構成されたTECHWANDO代表チームは、キョルギおよびプムセ部門で日頃の鍛錬の成果を遺憾なく発揮しました。\n\n"
                    "公式認定されたすべての獲得メダルと出場記録は、当サイトの「チャンピオン」および「メダリスト一覧」ページにてご覧いただけます。",
                    "東京国際オープン大会でのTECHWANDO代表チーム",
                ),
            },
            {
                "slug": "preparing-for-black-belt-dan-examination",
                "cat": cats["club-culture"],
                "tags": [t2, t3],
                "featured": False,
                "days_ago": 22,
                "colors": ("#111827", "#b91c1c"),
                "fa": (
                    "راهنمای کامل آمادگی برای آزمون ارتقای کمربند مشکی (دان ۱ تا ۳)",
                    "فهرست الزامات فنی، اخلاقی و نحوه ثبت درخواست ارتقای کمربند در پورتال اعضا.",
                    "رسیدن به کمربند مشکی پایان راه نیست، بلکه آغاز یادگیری عمیق هنرهای رزمی است. داوطلبان آزمون دان باید حداقل ۱۲ هفته پیش از تاریخ آزمون برنامه تمرینی خود را در سه محور پومسه، مبارزه آزاد و آمادگی جسمانی تنظیم کنند.\n\n"
                    "پس از قبولی در آزمون، اعضا می‌توانند از بخش «تاریخچه کمربند من» در پورتال شخصی، تصویر گواهینامه رسمی خود را جهت تأیید مدیریت بارگذاری نمایند.",
                    "کمربند مشکی تکواندو و گواهینامه دان",
                ),
                "ja": (
                    "黒帯昇段審査（初段〜三段）に向けた完全準備ガイド",
                    "技術課題・心構え、および会員ポータルからの昇段記録申請手順を詳しくご紹介します。",
                    "黒帯の取得はゴールではなく、真の武道修行の始まりです。受審者は審査日の12週間前から、指定プムセ、約束組手・自由組手、護身術、体力テストを計画的に仕上げましょう。\n\n"
                    "合格後は会員ポータルの「昇級・昇段履歴」から公式認定証をアップロードすることで、管理者の審査・承認を経て公認段位として登録されます。",
                    "黒帯昇段審査の準備イメージ",
                ),
            },
        ]

        now = timezone.now()
        for spec in posts:
            post, created = Post.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "category": spec["cat"],
                    "author": author,
                    "status": PublicationStatus.PUBLISHED,
                    "published_at": now - datetime.timedelta(days=spec["days_ago"]),
                    "is_featured": spec["featured"],
                },
            )
            post.tags.set(spec["tags"])
            if created or not post.featured_image:
                post.featured_image.save(
                    f"{spec['slug']}.png",
                    _make_card_png(*spec["colors"]),
                    save=True,
                )
            for code in ("fa", "ja"):
                title, excerpt, body, alt = spec[code]
                PostTranslation.objects.update_or_create(
                    post=post,
                    language=code,
                    defaults={
                        "title": title,
                        "excerpt": excerpt,
                        "body": body,
                        "featured_image_alt": alt,
                        "seo_title": title[:155],
                        "seo_description": excerpt[:300],
                    },
                )

    def _seed_products(self):
        cat_specs = [
            ("uniforms", 1, "لباس رزمی (دوبوک و دوگی)", "公式道着（ドボク・道衣）"),
            ("protective-gear", 2, "تجهیزات ایمنی و هوگو", "プロテクター・防具"),
            ("belts-training", 3, "کمربند و ابزار تمرین", "帯・トレーニング用品"),
        ]
        cats = {}
        for slug, order, fa, ja in cat_specs:
            c, _ = ProductCategory.objects.update_or_create(
                slug=slug, defaults={"display_order": order, "is_active": True}
            )
            ProductCategoryTranslation.objects.update_or_create(
                category=c, language="fa", defaults={"name": fa}
            )
            ProductCategoryTranslation.objects.update_or_create(
                category=c, language="ja", defaults={"name": ja}
            )
            cats[slug] = c

        items = [
            {
                "slug": "techwando-pro-black-collar-dobok",
                "sku": "TW-DBK-101",
                "cat": cats["uniforms"],
                "disc": Discipline.TAEKWONDO,
                "price": Decimal("14800.00"),
                "currency": "JPY",
                "featured": True,
                "colors": ("#111827", "#dc2626"),
                "fa": (
                    "دوبوک یقه‌مشکی مسابقاتی تکواندو مدل Pro",
                    "پارچه تنفس‌پذیر فوق‌سبک با استاندارد مسابقات رسمی کیوروگی و پومسه.",
                    "دوبوک حرفه‌ای تکواندو از الیاف میکروفایبر ضدتعریق با دوخت تقویت‌شده در نواحی شانه و زانو طراحی شده است تا بیشترین آزادی عمل را در ضربات بلند پا فراهم سازد.",
                    "جنس: ۶۵٪ پلی‌استر تنفسی، ۳۵٪ پنبه اعلا\nسایزبندی: ۱۵۰ تا ۲۰۰ سانتی‌متر\nیقه: مشکی رسمی ویژه دارندگان دان\nشست‌وشو: مقاوم در برابر تغییر فرم",
                ),
                "ja": (
                    "TECHWANDO プロ競技用 黒襟ドボク（公認モデル）",
                    "超軽量・高通気マイクロファイバー素材を採用した有段者向け公式道着。",
                    "激しいハイキックや回転動作を妨げない立体裁断と、吸汗速乾性に優れたハニカム織生地を採用。公式大会および昇段審査に最適な一着です。",
                    "素材：高機能ポリエステル65%・厳選コットン35%\nサイズ展開：150cm〜200cm\n襟仕様：有段者用ブラックVネック\n特徴：補強ステッチ・防縮加工済み",
                ),
            },
            {
                "slug": "reversible-competition-hogu-guard",
                "sku": "TW-HGU-204",
                "cat": cats["protective-gear"],
                "disc": Discipline.TAEKWONDO,
                "price": Decimal("11500.00"),
                "currency": "JPY",
                "featured": True,
                "colors": ("#1e3a8a", "#dc2626"),
                "fa": (
                    "هوگو دورو محافظ سینه مسابقاتی (آبی / قرمز)",
                    "جذب ضربه چندلایه EVA با طراحی ارگونومیک محافظ شانه و دنده.",
                    "محافظ سینه استاندارد باشگاهی و مسابقاتی با روکش چرم صنعتی مقاوم و فوم فشرده چندلایه برای حفاظت حداکثری در تمرینات کیوروگی.",
                    "رنگ: دورو (چونگ آبی / هونگ قرمز)\nفوم داخلی: EVA سه‌لایه ضربه‌گیر\nسایزبندی: ۱ تا ۵ (نوجوان تا بزرگسال)",
                ),
                "ja": (
                    "リバーシブル競技用チェストガード（青／赤 ホグ）",
                    "三層EVA衝撃吸収フォーム採用、肩・脇腹までしっかり守る人間工学設計。",
                    "高耐久PUレザーと軽量多層フォームを組み合わせ、強い蹴りの衝撃を効果的に分散。クラブ練習から公式試合まで幅広く対応します。",
                    "カラー：青（チョン）／赤（ホン）両面仕様\n内部構造：高密度3層EVAパッド\nサイズ：1号〜5号（ジュニア〜一般）",
                ),
            },
            {
                "slug": "master-embroidered-dan-black-belt",
                "sku": "TW-BLT-309",
                "cat": cats["belts-training"],
                "disc": Discipline.TAEKWONDO,
                "price": None,  # Demonstrates optional pricing!
                "currency": "JPY",
                "featured": True,
                "colors": ("#09090b", "#ca8a04"),
                "fa": (
                    "کمربند مشکی دان با گلدوزی اختصاصی فارسی و کره‌ای",
                    "کمربند کتان سنگین ۵ سانتی‌متری با گلدوزی طلایی نام ورزشکار و درجه دان.",
                    "ویژه اعضای تأییدشده کمربند مشکی باشگاه تکواندو. قیمت بر اساس تعداد خطوط گلدوزی فارسی و کره‌ای از طریق دفتر باشگاه استعلام می‌شود.",
                    "عرض کمربند: ۵ سانتی‌متر استاندارد اساتید\nهسته داخلی: کتان دولایه فشرده\nسفارشی‌سازی: گلدوزی نام به فارسی و کره‌ای",
                ),
                "ja": (
                    "特製刺繍入り 黒帯（日本語・ペルシャ語名入れ対応）",
                    "重厚な5cm幅コットン芯地仕様、金糸による氏名・段位オーダー刺繍対応。",
                    "TECHWANDO公認有段者向けの特別仕立て黒帯です。刺繍文字数・仕様に応じたクラブ窓口お見積り品（価格お問い合わせ）となります。",
                    "帯幅：5.0cm（本絹風高密度コットン）\n刺繍：金糸（日本語・ペルシャ語両対応）\n長さ：260cm〜320cm",
                ),
            },
            {
                "slug": "double-clapper-kicking-target-paddle",
                "sku": "TW-PAD-412",
                "cat": cats["belts-training"],
                "disc": Discipline.KARATE,
                "price": Decimal("4200.00"),
                "currency": "JPY",
                "featured": True,
                "colors": ("#1f2937", "#16a34a"),
                "fa": (
                    "میت دوبل تمرینی ضربات سرعتی و ترکیبی",
                    "دسته ضدلغزش با بند مچی تقویت‌شده و صدای شفاف برخورد برای سنجش دقت ضربه.",
                    "ابزار ضروری برای تمرینات سرعت، زمان‌بندی و ضربات چرخشی در تکواندو و کاراته با دوام بالا در برابر تمرینات سنگین روزانه.",
                    "طول: ۴۱ سانتی‌متر\nروکش: میکروفایبر مقاوم ضدپارگی\nبند ایمنی: کش پهن محافظ مچ",
                ),
                "ja": (
                    "ダブルハンドミット（スピード・連続蹴り練習用）",
                    "正確なミートを快音でフィードバックする高耐久トレーニングミット。",
                    "テコンドーや空手の連続蹴り・回転技の精度向上に最適。滑り止めグリップと強化リストストラップにより安全に保持できます。",
                    "全長：41cm\n外皮：耐摩耗マイクロファイバーレザー\n付属品：高弾性リストストラップ",
                ),
            },
        ]
        for spec in items:
            prod, _ = Product.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "sku": spec["sku"],
                    "category": spec["cat"],
                    "discipline": spec["disc"],
                    "price": spec["price"],
                    "currency": spec["currency"],
                    "is_available": True,
                    "is_featured": spec["featured"],
                    "status": PublicationStatus.PUBLISHED,
                },
            )
            for code in ("fa", "ja"):
                name, short, desc, sp = spec[code]
                ProductTranslation.objects.update_or_create(
                    product=prod,
                    language=code,
                    defaults={
                        "name": name,
                        "short_description": short,
                        "description": desc,
                        "specifications": sp,
                        "seo_title": name[:155],
                        "seo_description": short[:300],
                    },
                )
            if not prod.images.exists():
                pi = ProductImage(
                    product=prod,
                    alt_text_fa=spec["fa"][0],
                    alt_text_ja=spec["ja"][0],
                    is_primary=True,
                    display_order=0,
                )
                pi.image.save(
                    f"{spec['sku'].lower()}.png",
                    _make_card_png(*spec["colors"]),
                    save=True,
                )

    def _seed_accounts_and_athletes(self, comps: list[Competition], password: str) -> User:
        staff_specs = [
            ("admin@techwando.example.com", "آرش", "کاظمی", UserRole.SUPER_ADMIN, "fa"),
            ("content@techwando.example.com", "سارا", "مرادی", UserRole.CONTENT_ADMIN, "fa"),
            ("manager@techwando.example.com", "Kenji", "Takahashi", UserRole.CLUB_MANAGER, "ko"),
            ("moderator@techwando.example.com", "Yuki", "Sato", UserRole.MODERATOR, "ko"),
        ]
        staff_users = {}
        for email, fn, ln, role, lang in staff_specs:
            user = User.objects.filter(email=email).first()
            if not user:
                if role == UserRole.SUPER_ADMIN:
                    user = User.objects.create_superuser(
                        email=email,
                        password=password,
                        first_name=fn,
                        last_name=ln,
                        preferred_language=lang,
                    )
                else:
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        first_name=fn,
                        last_name=ln,
                        role=role,
                        preferred_language=lang,
                    )
            staff_users[role] = user

        reviewer = staff_users[UserRole.CLUB_MANAGER]
        dan3 = BeltType.objects.get(discipline=Discipline.TAEKWONDO, rank_code="3-DAN")
        dan2_tkd = BeltType.objects.get(discipline=Discipline.TAEKWONDO, rank_code="2-DAN")
        dan2_kar = BeltType.objects.get(discipline=Discipline.KARATE, rank_code="2-DAN")
        dan1_judo = BeltType.objects.get(discipline=Discipline.JUDO, rank_code="1-DAN")

        athletes = [
            {
                "email": "parisa.rahimi@techwando.example.com",
                "fn": "پریسا",
                "ln": "رحیمی",
                "fn_ja": "パリサ",
                "ln_ja": "ラヒミ",
                "lang": "fa",
                "disc": Discipline.TAEKWONDO,
                "public": True,
                "bio_fa": "قهرمان کیوروگی و پومسه با ۸ سال سابقه عضویت در تیم منتخب آکادمی تکواندو و مربی رده نوجوانان.",
                "bio_ja": "TECHWANDO所属8年。キョルギ・プムセ両部門で国際大会入賞歴を持ち、ジュニアクラス指導補佐も務める。",
                "belt": (dan3, datetime.date(2025, 9, 15)),
                "medal": (MedalType.GOLD, comps[0], "-57kg Senior Kyorugi", datetime.date(2026, 5, 16)),
                "ach": (
                    "قهرمان وزن منفی ۵۷ کیلوگرم اوپن بین‌المللی توکیو",
                    "東京国際オープン 女子57kg級 優勝",
                    datetime.date(2026, 5, 16),
                    comps[0],
                ),
                "act": (
                    "برگزاری کارگاه رایگان دفاع شخصی ویژه دانش‌آموزان",
                    "地域小中学生向け 無料護身術・礼法ワークショップ開催",
                    datetime.date(2026, 6, 20),
                    "توکیو — مرکز فرهنگی شیبویا",
                    "東京都渋谷区スポーツセンター",
                    True,
                ),
            },
            {
                "email": "haruto.yamamoto@techwando.example.com",
                "fn": "هاروتو",
                "ln": "یاماموتو",
                "fn_ja": "陽翔",
                "ln_ja": "山本",
                "lang": "ko",
                "disc": Discipline.TAEKWONDO,
                "public": True,
                "bio_fa": "ملی‌پوش رده بزرگسالان تکواندو و دارنده مدال طلای پومسه انفرادی در رقابت‌های بین‌المللی توکیو.",
                "bio_ja": "シニア男子プムセ・キョルギ代表選手。正確な基本技と高い跳躍力を武器に国際大会で活躍。",
                "belt": (dan2_tkd, datetime.date(2025, 6, 10)),
                "medal": (MedalType.GOLD, comps[0], "Senior Individual Poomsae", datetime.date(2026, 5, 15)),
                "ach": (
                    "کسب بالاترین امتیاز فنی پومسه انفرادی در توکیو ۲۰۲۶",
                    "2026年東京国際オープン 男子個人プムセ最優秀技術賞",
                    datetime.date(2026, 5, 15),
                    comps[0],
                ),
                "act": (
                    "داوری داوطلبانه جشنواره ورزشی نوجوانان",
                    "青少年武道交流フェスティバル ボランティア審判員",
                    datetime.date(2026, 7, 5),
                    "یوکوهاما، ژاپن",
                    "神奈川県横浜市",
                    True,
                ),
            },
            {
                "email": "amir.hosseini@techwando.example.com",
                "fn": "امیرحسین",
                "ln": "حسینی",
                "fn_ja": "アミルホセイン",
                "ln_ja": "ホセイニ",
                "lang": "fa",
                "disc": Discipline.KARATE,
                "public": True,
                "bio_fa": "متخصص کاتا و کومیته و دارنده مدال نقره جام دوستی هنرهای رزمی تهران — کیوتو.",
                "bio_ja": "空手道・形および組手の競技選手。テヘラン・京都友好武道大会にて銀メダルを獲得。",
                "belt": (dan2_kar, datetime.date(2025, 4, 22)),
                "medal": (MedalType.SILVER, comps[1], "Senior Individual Kata", datetime.date(2026, 3, 9)),
                "ach": (
                    "نایب‌قهرمانی کاتا انفرادی جام دوستی تهران — کیوتو",
                    "テヘラン・京都友好武道大会 シニア個人形 準優勝",
                    datetime.date(2026, 3, 9),
                    comps[1],
                ),
                "act": None,
            },
            {
                "email": "aoi.nakamura@techwando.example.com",
                "fn": "آئویی",
                "ln": "ناکامورا",
                "fn_ja": "葵",
                "ln_ja": "中村",
                "lang": "ko",
                "disc": Discipline.JUDO,
                "public": True,
                "bio_fa": "ورزشکار جودو و مربی آمادگی جسمانی باشگاه با سابقه کسب مدال برنز مسابقات دعوتی اوساکا.",
                "bio_ja": "柔道初段・フィジカルコーチ。大阪選抜柔道招待大会にて銅メダルと礼節賞を受賞。",
                "belt": (dan1_judo, datetime.date(2025, 2, 18)),
                "medal": (MedalType.BRONZE, comps[2], "-73kg Invitational", datetime.date(2025, 11, 3)),
                "ach": (
                    "دریافت تندیس اخلاق و پهلوانی مسابقات اوساکا ۲۰۲۵",
                    "2025年大阪選抜柔道招待大会 礼節賞受賞",
                    datetime.date(2025, 11, 3),
                    comps[2],
                ),
                "act": None,
            },
            {
                # Private member (consent=False) — verifies public pages respect privacy
                "email": "member@techwando.example.com",
                "fn": "نیما",
                "ln": "رضایی",
                "fn_ja": "ニマ",
                "ln_ja": "レザイ",
                "lang": "fa",
                "disc": Discipline.TAEKWONDO,
                "public": False,
                "bio_fa": "عضو فعال باشگاه در حال آمادگی برای آزمون دان دو.",
                "bio_ja": "二段昇段審査に向けて鍛錬中のクラブ会員。",
                "belt": (dan2_tkd, datetime.date(2026, 1, 20)),
                "medal": None,
                "ach": None,
                "act": None,
            },
        ]

        for a in athletes:
            if User.objects.filter(email=a["email"]).exists():
                continue
            u = User.objects.create_user(
                email=a["email"],
                password=password,
                first_name=a["fn"],
                last_name=a["ln"],
                role=UserRole.MEMBER,
                preferred_language=a["lang"],
            )
            profile = create_member_profile_with_application(
                user=u,
                first_name=a["fn"],
                last_name=a["ln"],
                phone="+81-3-5555-0199",
                primary_discipline=a["disc"],
            )
            profile.first_name_ja = a["fn_ja"]
            profile.last_name_ja = a["ln_ja"]
            profile.biography = a["bio_fa"]
            profile.biography_ja = a["bio_ja"]
            profile.birth_date = datetime.date(1999, 4, 12)
            profile.public_profile_consent = a["public"]
            profile.public_profile_visibility = a["public"]
            profile.save()
            review_membership_application(
                profile=profile,
                reviewer=reviewer,
                new_status=MembershipStatus.APPROVED,
                note="Verified active club athlete.",
            )

            belt_type, belt_date = a["belt"]
            bh = BeltHistory.objects.create(
                member=profile,
                belt_type=belt_type,
                discipline=belt_type.discipline,
                award_date=belt_date,
                issuing_authority="Kukkiwon / TECHWANDO Technical Board",
            )
            ModerationService.review_submission(
                bh, reviewer=reviewer, new_status=ApprovalStatus.APPROVED, note="Certificate verified."
            )

            if a["medal"]:
                mtype, comp, div, mdate = a["medal"]
                medal = Medal.objects.create(
                    member=profile,
                    medal_type=mtype,
                    discipline=a["disc"],
                    competition=comp,
                    competition_name=comp.title_fa,
                    competition_name_ja=comp.title_ja,
                    competition_location=comp.location_fa,
                    competition_location_ja=comp.location_ja,
                    division_category=div,
                    award_date=mdate,
                )
                ModerationService.review_submission(
                    medal,
                    reviewer=reviewer,
                    new_status=ApprovalStatus.APPROVED,
                    note="Official podium result verified.",
                )
                part = CompetitionParticipation.objects.create(
                    member=profile,
                    competition=comp,
                    division_category=div,
                    result=f"مدال {medal.get_medal_type_display()}",
                    result_ja=f"{mtype} メダリスト",
                    placement=1 if mtype == MedalType.GOLD else (2 if mtype == MedalType.SILVER else 3),
                )
                ModerationService.review_submission(
                    part, reviewer=reviewer, new_status=ApprovalStatus.APPROVED
                )

            if a["ach"]:
                t_fa, t_ja, adate, acomp = a["ach"]
                ach = Achievement.objects.create(
                    member=profile,
                    title=t_fa,
                    title_ja=t_ja,
                    discipline=a["disc"],
                    competition=acomp,
                    achievement_date=adate,
                )
                ModerationService.review_submission(
                    ach, reviewer=reviewer, new_status=ApprovalStatus.APPROVED
                )

            if a["act"]:
                at_fa, at_ja, act_date, loc_fa, loc_ja, consent = a["act"]
                act = SocialActivity.objects.create(
                    member=profile,
                    title=at_fa,
                    title_ja=at_ja,
                    description=at_fa,
                    description_ja=at_ja,
                    activity_date=act_date,
                    location=loc_fa,
                    location_ja=loc_ja,
                    public_visibility_consent=consent,
                )
                ModerationService.review_submission(
                    act,
                    reviewer=staff_users[UserRole.MODERATOR],
                    new_status=ApprovalStatus.APPROVED,
                    note="Exemplary community contribution.",
                )

            # Add one PENDING submission on the demo member account so admin queue is live
            if not a["public"]:
                Medal.objects.create(
                    member=profile,
                    medal_type=MedalType.SILVER,
                    discipline=Discipline.TAEKWONDO,
                    competition=comps[0],
                    competition_name=comps[0].title_fa,
                    competition_name_ja=comps[0].title_ja,
                    competition_location=comps[0].location_fa,
                    competition_location_ja=comps[0].location_ja,
                    division_category="-68kg Senior Sparring",
                    award_date=datetime.date(2026, 5, 17),
                    approval_status=ApprovalStatus.PENDING,
                )

        if not ContactMessage.objects.exists():
            ContactMessage.objects.create(
                name="Takeshi Mori",
                email="mori@example.jp",
                subject="ジュニアクラス体験入会について",
                message="10歳の息子のテコンドー体験レッスンを希望しております。週末のスケジュールを教えてください。",
                language="ja",
            )

        return staff_users[UserRole.CONTENT_ADMIN]
