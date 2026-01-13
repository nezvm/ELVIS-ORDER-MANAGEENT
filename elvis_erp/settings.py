from pathlib import Path

from decouple import config
from django.utils.translation import gettext_lazy as _


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="mu2zt*8$t6pb926p443ig@-*zi*(v23csz_*7l-yo0hfqr2%8#")

DEBUG = config("DEBUG", default=True, cast=bool)


ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000", 
    "http://127.0.0.1:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "https://modular-elvis.preview.emergentagent.com",
    "https://modular-elvis.preview.emergentagent.com",
]

# Application definition

INSTALLED_PLUGINS = [
    "admin_interface",
    "colorfield",
    "compressor",
    "crispy_bootstrap5",
    "crispy_forms",
    "django_extensions",
    "django_filters",
    "django_tables2",
    "import_export",
    "registration",
    "tinymce",
    "easy_thumbnails",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.humanize",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "user_sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
MODULES = [
    "master",
    "core",
    "accounts",
    "channels_config",
    "logistics",
    "inventory",
    "segmentation",
    "integrations",
    "api",
    "marketing",
]

INSTALLED_APPS = INSTALLED_PLUGINS + DJANGO_APPS + MODULES

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "user_sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]

ROOT_URLCONF = "elvis_erp.urls"

THUMBNAIL_ALIASES = {"": {"avatar": {"size": (50, 50), "crop": True}}}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.main_context",
            ]
        },
    }
]

WSGI_APPLICATION = "elvis_erp.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": config("DB_NAME", default=BASE_DIR / "db.sqlite3"),
        "USER": config("DB_USER", default=""),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default=""),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = []

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)


# Django Compressor Settings
COMPRESS_ENABLED = False
COMPRESS_CSS_HASHING_METHOD = "content"
COMPRESS_FILTERS = {"css": ["compressor.filters.css_default.CssAbsoluteFilter", "compressor.filters.cssmin.rCSSMinFilter"], "js": ["compressor.filters.jsmin.JSMinFilter"]}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019", "admin.E410"]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

SESSION_ENGINE = "user_sessions.backends.db"
SESSION_CACHE_ALIAS = "default"
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_L10N = True
USE_TZ = True

USE_L10N = False
DATE_INPUT_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y", "%d %b, %Y", "%d %b %Y", "%d %b, %Y", "%d %B, %Y", "%d %B %Y")
DATETIME_INPUT_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M", "%d/%m/%y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")
SHORT_DATETIME_FORMAT = "d/m/Y g:i A"
SHORT_DATE_FORMAT = "d/m/Y"

# Static files (CSS, JavaScript, Images)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "/static/"
STATIC_FILE_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = ((BASE_DIR / "static"),)
STATIC_ROOT = BASE_DIR / "assets"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = True
SEND_ACTIVATION_EMAIL = False
REGISTRATION_EMAIL_SUBJECT_PREFIX = ""

REGISTRATION_OPEN = True
LOGIN_URL = "/accounts/login/"
LOGOUT_URL = "/accounts/logout/"
LOGIN_REDIRECT_URL = "/"


EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
ACCOUNT_EMAIL_VERIFICATION = "none"
SITE_ID = 1

if DEBUG is False:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
    COMPRESS_ENABLED = False
    X_FRAME_OPTIONS = "DENY"
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    HTML_MINIFY = True
    KEEP_COMMENTS_ON_MINIFYING = False

LOCALE_PATHS = (BASE_DIR / "locale",)
LANGUAGES = (("en", _("English")), ("ml", _("Malayalam")), ("hi", _("Hindi")), ("ta", _("Tamil")))


APP_SETTINGS = {
    "logo": "/static/app/images/elvis.webp",
    "logo_mini": "/static/app/config/logo_mini.png",
    "favicon": "/static/app/config/favicon.png",
    "site_name": "Elvis-Manager",
    "site_title": "Elvis-Manager | Efficiency amplified, productivity perfected.",
    "site_description": "Efficiency amplified, productivity perfected.",
    "site_keywords": "Efficiency amplified, productivity perfected.",
    "background_image": "/static/app/config/background.jpg",
}

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Elvis-Manager ERP API",
    "DESCRIPTION": "RESTful API for Elvis-Manager ERP System",
    "VERSION": "1.0.0",
}

# Celery Configuration
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"



# =============================================================================
# FEATURE FLAGS
# =============================================================================
# Enable/disable modules without code changes
FEATURE_FLAGS = {
    # Core Module Toggles
    'ENABLE_LOGISTICS_MODULE': True,      # Carrier management, shipping rules, NDR
    'ENABLE_INVENTORY_MODULE': True,      # Warehouse, stock levels, movements
    'ENABLE_SEGMENTATION_MODULE': True,   # Customer profiles, segments, cohorts
    'ENABLE_MARKETING_MODULE': True,      # Leads, campaigns, market insights
    'ENABLE_INTEGRATIONS_MODULE': True,   # Shopify, Google, webhooks
    'ENABLE_DYNAMIC_CHANNELS': True,      # DynamicChannel config (vs static Channel)
    
    # Legacy Fallbacks
    'USE_LEGACY_SHIPPING': False,         # Use old courier_partner.py functions
    
    # Feature-specific toggles
    'ENABLE_COHORT_ANALYSIS': True,
    'ENABLE_WHATSAPP_INTEGRATION': False,  # Requires Meta Cloud API setup
    'ENABLE_SHOPIFY_INTEGRATION': False,   # Requires Shopify API credentials
    'ENABLE_GOOGLE_CONTACTS_SYNC': False,  # Requires Google Workspace setup
}

# =============================================================================
# CARRIER CREDENTIALS (Fallback - prefer database CarrierCredential model)
# =============================================================================
# These are used only if database credentials are not configured
# In production, use the admin panel to configure CarrierCredential

# Delhivery
DELHIVERY_API_TOKEN = config('DELHIVERY_API_TOKEN', default='')
DELHIVERY_PICKUP_NAME = config('DELHIVERY_PICKUP_NAME', default='Elvis co')

# BlueDart
BLUEDART_CLIENT_ID = config('BLUEDART_CLIENT_ID', default='')
BLUEDART_CLIENT_SECRET = config('BLUEDART_CLIENT_SECRET', default='')
BLUEDART_LICENCE_KEY = config('BLUEDART_LICENCE_KEY', default='')
BLUEDART_LOGIN_ID = config('BLUEDART_LOGIN_ID', default='')
BLUEDART_CUSTOMER_CODE = config('BLUEDART_CUSTOMER_CODE', default='')
BLUEDART_SHIPPER_NAME = config('BLUEDART_SHIPPER_NAME', default='')
BLUEDART_SHIPPER_MOBILE = config('BLUEDART_SHIPPER_MOBILE', default='')
BLUEDART_SHIPPER_PINCODE = config('BLUEDART_SHIPPER_PINCODE', default='')
BLUEDART_ORIGIN_AREA = config('BLUEDART_ORIGIN_AREA', default='')

# TPC (Professional Couriers)
TPC_CLIENT_CODE = config('TPC_CLIENT_CODE', default='')
TPC_PASSWORD = config('TPC_PASSWORD', default='')
TPC_SENDER_NAME = config('TPC_SENDER_NAME', default='Elvis Co')
TPC_SENDER_CODE = config('TPC_SENDER_CODE', default='')
TPC_SENDER_ADDRESS = config('TPC_SENDER_ADDRESS', default='')
TPC_SENDER_CITY = config('TPC_SENDER_CITY', default='')
TPC_SENDER_PINCODE = config('TPC_SENDER_PINCODE', default='')
TPC_SENDER_MOBILE = config('TPC_SENDER_MOBILE', default='')
TPC_SENDER_EMAIL = config('TPC_SENDER_EMAIL', default='')
TPC_SENDER_GSTIN = config('TPC_SENDER_GSTIN', default='')

# DTDC
DTDC_API_KEY = config('DTDC_API_KEY', default='')
DTDC_CUSTOMER_CODE = config('DTDC_CUSTOMER_CODE', default='')
