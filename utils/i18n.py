async def load_translations() -> None:
    """
    Unified method to load translations from all sources.

    This function loads translations in the following order:
    1. Default fallback translations (hardcoded)
    2. Local files (from translations directory)
    3. Database (overrides previous sources)

    The loading is done sequentially to ensure proper override priority.
    """
    try:
        # 1. First set up default fallback translations
        _initialize_default_translations()

        # 2. Then load from files
        await _load_translations_from_files()

        # 3. Finally, try to load from database (which may override file translations)
        await _load_translations_from_database()

        logger.info(
            f"Loaded translations successfully: {len(_translations['en_US'])} English, "
            f"{len(_translations['ru_RU'])} Russian keys"
        )
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")
        logger.info("Continuing with default translations only")


def _initialize_default_translations() -> None:
    """Initialize default fallback translations."""
    # Default English translations
    _translations["en_US"].update({
        "Yes": "Yes",
        "No": "No",
        "Back": "Back",
        "Cancel": "Cancel",
        "Confirm": "Confirm",
        # Add more default translations as needed
    })

    # Default Russian translations
    _translations["ru_RU"].update({
        "Yes": "Да",
        "No": "Нет",
        "Back": "Назад",
        "Cancel": "Отмена",
        "Confirm": "Подтвердить",
        # Add more default translations as needed
    })


async def _load_translations_from_files() -> None:
    """Load translations from JSON files with improved error handling."""
    # Path to translations directory
    translations_dir = os.path.join(os.path.dirname(__file__), "../translations")

    # Create the directory if it doesn't exist
    os.makedirs(translations_dir, exist_ok=True)

    # Load for each supported language
    for lang_code in ["en_US", "ru_RU"]:
        lang_path = os.path.join(translations_dir, f"{lang_code}.json")

        try:
            if os.path.exists(lang_path):
                with open(lang_path, "r", encoding="utf-8") as f:
                    _translations[lang_code].update(json.load(f))
                    logger.info(f"Loaded {lang_code} translations from file: {len(_translations[lang_code])} keys")
            else:
                # Create an empty translations file for future use
                with open(lang_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
                    logger.info(f"Created empty {lang_code} translations file")
        except Exception as e:
            logger.error(f"Error loading translation file {lang_path}: {str(e)}")


async def _load_translations_from_database() -> None:
    """Load translations from the database with unified error handling."""
    try:
        # Try using the db_client method first
        from db.db_client import db_operation

        async def fetch_translations():
            from db.supabase_client import get_supabase
            client = get_supabase()
            response = client.from_("translations").schema("game").select("translation_key,en_US,ru_RU").execute()
            return response.data if hasattr(response, 'data') else None

        translations_data = await db_operation(
            "load_translations_from_database",
            fetch_translations,
            default_return=[]
        )

        # Process the translations
        if translations_data:
            loaded_count = 0
            for translation in translations_data:
                key = translation.get("translation_key", "")
                if key:
                    _translations["en_US"][key] = translation.get("en_US", key)
                    _translations["ru_RU"][key] = translation.get("ru_RU", key)
                    loaded_count += 1

            logger.info(f"Loaded {loaded_count} translations from database")
        else:
            logger.info("No translations found in database")
    except Exception as e:
        logger.warning(f"Error loading translations from database: {e}")