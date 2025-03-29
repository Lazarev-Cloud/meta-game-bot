async def validate_name(event, state, context):
    name = context.get("result", "").strip()

    if len(name) < 2:
        await event.answer("Имя слишком короткое. Минимум 2 символа.")
        raise ValueError("Invalid name")

    # optionally normalize
    normalized = name.capitalize()
    await state.update_data(name=normalized)


async def save_name_to_state(event, state, context):
    data = await state.get_data()
    name = data.get("name")
    await state.update_data(validated_name=name)
