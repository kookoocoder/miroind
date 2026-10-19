"""\n配置管理\n统一从项目根目录的 .env 文件加载配置\n"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    # Keep explicit process environment values authoritative. This lets
    # `npm run dev:miroind` enable offline mode even when a developer has a
    # `.env` file copied from the hosted-provider example.
    load_dotenv(project_root_env, override=False)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=False)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')

    # The MiroInd MVP can run without hosted provider credentials. Set this
    # explicitly for local/offline development; upstream graph simulations
    # still require both provider keys.
    MIROIND_OFFLINE_ONLY = os.environ.get('MIROIND_OFFLINE_ONLY', 'false').lower() == 'true'
    
    # BOSS media uploads use a separate catalog and keep binary content out of
    # scenario JSON.  The global Flask limit remains at least the legacy 50MB
    # limit while allowing the BOSS-specific default of 100MB.
    BOSS_ASSETS_DIR = os.environ.get(
        'BOSS_ASSETS_DIR',
        os.path.join(os.path.dirname(__file__), '../uploads/boss/assets')
    )
    BOSS_MAX_ASSET_BYTES = int(os.environ.get('BOSS_MAX_ASSET_BYTES', str(100 * 1024 * 1024)))
    BOSS_ALLOWED_MEDIA_MIMES = frozenset(
        item.strip().lower()
        for item in os.environ.get(
            'BOSS_ALLOWED_MEDIA_MIMES',
            ','.join(
                (
                    'text/plain', 'text/markdown', 'text/csv', 'text/tab-separated-values',
                    'text/html', 'application/json', 'application/xml', 'application/yaml',
                    'application/rtf', 'application/pdf',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'image/png', 'image/jpeg', 'image/gif', 'image/webp',
                    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/mp4',
                    'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo',
                    'video/x-matroska',
                )
            ),
        ).split(',')
        if item.strip()
    )

    # Existing upstream uploads retain their 50MB behavior.  BOSS requests
    # are still checked against BOSS_MAX_ASSET_BYTES in the catalog service.
    MAX_CONTENT_LENGTH = max(50 * 1024 * 1024, BOSS_MAX_ASSET_BYTES)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Credential-free MiroInd runs are stored separately from upstream state.
    MIROIND_RUNS_DIR = os.environ.get(
        'MIROIND_RUNS_DIR',
        os.path.join(os.path.dirname(__file__), '../uploads/miroind/runs')
    )

    BOSS_SCENARIOS_DIR = os.environ.get(
        'BOSS_SCENARIOS_DIR',
        os.path.join(os.path.dirname(__file__), '../uploads/boss/scenarios')
    )

    # Optional model-backed BOSS reviews. These values are intentionally
    # environment-only; credentials must never be persisted in run records.
    BOSS_MODEL_ENABLED = os.environ.get('BOSS_MODEL_ENABLED', 'false').lower() == 'true'
    BOSS_MODEL_PROVIDER = os.environ.get('BOSS_MODEL_PROVIDER', 'opencode')
    _BOSS_MODEL_API_KEY = os.environ.get('BOSS_MODEL_API_KEY')
    BOSS_MODEL_API_KEY = (
        _BOSS_MODEL_API_KEY
        if _BOSS_MODEL_API_KEY and _BOSS_MODEL_API_KEY != 'your_model_api_key_here'
        else os.environ.get('DEEPSEEK_API_KEY')
    )
    BOSS_MODEL_BASE_URL = os.environ.get('BOSS_MODEL_BASE_URL', 'https://api.deepseek.com/v1')
    BOSS_MODEL_NAME = os.environ.get('BOSS_MODEL_NAME', 'omnirush/gpt-6-astra')
    BOSS_MODEL_MAX_TOKENS = int(os.environ.get('BOSS_MODEL_MAX_TOKENS', '1200'))
    BOSS_MODEL_TIMEOUT_SECONDS = int(os.environ.get('BOSS_MODEL_TIMEOUT_SECONDS', '120'))
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls) -> list[str]:
        """验证必要配置"""
        errors: list[str] = []
        if not cls.MIROIND_OFFLINE_ONLY and not cls.BOSS_MODEL_ENABLED:
            if not cls.LLM_API_KEY:
                errors.append("LLM_API_KEY 未配置")
            if not cls.ZEP_API_KEY:
                errors.append("ZEP_API_KEY 未配置")
        elif (
            not cls.MIROIND_OFFLINE_ONLY
            and cls.BOSS_MODEL_ENABLED
            and cls.BOSS_MODEL_PROVIDER != 'opencode'
            and not cls.BOSS_MODEL_API_KEY
        ):
            errors.append("BOSS_MODEL_API_KEY or DEEPSEEK_API_KEY 未配置")
        if os.environ.get("ZEP_API_URL"):
            errors.append("ZEP_API_URL 不受支持；MiroFish 仅连接 Zep Cloud")
        if cls.DEBUG:
            import warnings
            warnings.warn("Flask DEBUG mode is enabled. Do not use in production.", RuntimeWarning)
        return errors
