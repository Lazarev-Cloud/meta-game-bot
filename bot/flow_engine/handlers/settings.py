async def set_lang_ru(event, state, context):
    await state.update_data(lang="ru")


async def set_lang_en(event, state, context):
    await state.update_data(lang="en")
