Error - Could
not find
the
file
by
path / tests / test_start_command.py
for qodo_structured_read_filesimport unittest
    from unittest.mock import AsyncMock, patch
from telegram import User, Message, Update
from telegram.ext import CallbackContext

from bot.states import start_command


class TestStartCommand(unittest.TestCase):
    def setUp(self):
        self.user = User(id=123, first_name='Test', is_bot=False)
        self.message = Message(message_id=1, date=None, chat=None, text='/start', from_user=self.user)
        self.update = Update(update_id=1, message=self.message)
        self.context = CallbackContext(bot=None, application=None, user_data={}, chat_data={})

    @patch('bot.states._', return_value="Sorry, the service is currently unreachable. Please try again later.")
    @patch('bot.states.player_exists', new_callable=AsyncMock)
    @patch('bot.states.get_language_keyboard', return_value=['KeyboardMarkup'])
    async def test_start_new_player(self, mock_get_language_keyboard, mock_player_exists):
        mock_player_exists.return_value = False

        await start_command(self.update, self.context)

        # Ensure the player check is called with the correct arguments
        mock_player_exists.assert_called_once_with(str(self.user.id))

        # Check message was sent
        self.assertEqual(self.update.message.reply_text.call_count, 1)
        self.update.message.reply_text.assert_called_with(
            "Welcome to Novi-Sad, a city at the crossroads of Yugoslavia's future! "
            "Please select your preferred language:\n\n"
            "Добро пожаловать в Нови-Сад, город на перекрестке будущего Югославии! "
            "Пожалуйста, выберите предпочитаемый язык:",
            reply_markup=['KeyboardMarkup']
        )

    @patch('bot.states.player_exists', new_callable=AsyncMock)
    @patch('bot.states.start_command', new_callable=AsyncMock)
    async def test_start_existing_player(self, mock_start_command, mock_player_exists):
        mock_player_exists.return_value = True

        await start_command(self.update, self.context)

        mock_player_exists.assert_called_once_with(str(self.user.id))
        mock_start_command.assert_called_once_with(self.update, self.context)

    @patch('bot.states._', return_value="Sorry, we're experiencing technical difficulties. Please try again later.")
    @patch('bot.states.player_exists', new_callable=AsyncMock)
    async def test_start_player_check_error(self, mock_player_exists, mock_translate):
        mock_player_exists.side_effect = Exception("Database connection error")

        await start_command(self.update, self.context)

        self.assertEqual(self.update.message.reply_text.call_count, 1)
        self.update.message.reply_text.assert_called_with(
            "Sorry, we're experiencing technical difficulties. Please try again later."
        )

    async def test_start_player_check_timeout(self, mock_player_exists, mock_translate):
        mock_player_exists.side_effect = TimeoutError("Service timed out")

        await start_command(self.update, self.context)

        self.assertEqual(self.update.message.reply_text.call_count, 1)
        self.update.message.reply_text.assert_called_with(
            "Sorry, the service is currently unreachable. Please try again later."
        )


if __name__ == '__main__':
    unittest.main()
