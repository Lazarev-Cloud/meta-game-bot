from bot.flow_engine.exceptions.base import NameTooShortError


async def validate_name(event, state, context):
    data = await state.get_data()
    name = data.get("name", "")
    if len(name) < 3:
        raise NameTooShortError("Name too short")
    elif len(name) > 8:
        raise ValueError("__system__.invalid_text")


async def save_name_to_state(event, state, context):
    data = await state.get_data()
    name = data.get("name")
    await state.update_data(validated_name=name)
