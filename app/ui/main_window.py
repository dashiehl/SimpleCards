from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from app.config import APP_NAME
from app.db import deck_repository
from app.db.connection import db_session
from app.ui.widgets.card_browser import CardBrowser
from app.ui.widgets.deck_browser import DeckBrowser
from app.ui.widgets.deck_settings_screen import DeckSettingsScreen
from app.ui.widgets.history_screen import HistoryScreen
from app.ui.widgets.import_screen import ImportScreen
from app.ui.widgets.learn_screen import LearnScreen
from app.ui.widgets.match_screen import MatchScreen
from app.ui.widgets.new_deck_dialog import NewDeckDialog
from app.ui.widgets.settings_screen import SettingsScreen
from app.ui.widgets.stats_screen import StatsScreen
from app.ui.widgets.study_hub_screen import StudyHub
from app.ui.widgets.study_session import StudySession
from app.ui.widgets.test_screen import TestScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 750)

        self._current_deck_id: int | None = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.deck_browser = DeckBrowser()
        self.study_hub = StudyHub()
        self.study_session = StudySession()
        self.match_screen = MatchScreen()
        self.learn_screen = LearnScreen()
        self.test_screen = TestScreen()
        self.import_screen = ImportScreen()
        self.card_browser = CardBrowser()
        self.stats_screen = StatsScreen()
        self.deck_settings_screen = DeckSettingsScreen()
        self.settings_screen = SettingsScreen()
        self.history_screen = HistoryScreen()

        for widget in (self.deck_browser, self.study_hub, self.study_session, self.match_screen,
                       self.learn_screen, self.test_screen, self.import_screen, self.card_browser,
                       self.stats_screen, self.deck_settings_screen, self.settings_screen, self.history_screen):
            self.stack.addWidget(widget)

        self.deck_browser.study_requested.connect(self._open_study_hub)
        self.deck_browser.browse_requested.connect(self._open_card_browser)
        self.deck_browser.stats_requested.connect(self._open_stats)
        self.deck_browser.settings_requested.connect(self._open_deck_settings)
        self.deck_browser.history_requested.connect(self._open_history)
        self.deck_browser.new_deck_requested.connect(self._create_deck)
        self.deck_browser.import_requested.connect(self._open_import)
        self.deck_browser.preferences_requested.connect(self._open_settings)

        self.study_hub.back_requested.connect(self._back_to_browser)
        self.study_hub.flashcards_requested.connect(self._open_study_session)
        self.study_hub.match_requested.connect(self._open_match)
        self.study_hub.learn_requested.connect(self._open_learn)
        self.study_hub.test_requested.connect(self._open_test)

        self.study_session.finished.connect(self._back_to_hub)
        self.match_screen.back_requested.connect(self._back_to_hub)
        self.learn_screen.back_requested.connect(self._back_to_hub)
        self.test_screen.back_requested.connect(self._back_to_hub)
        self.history_screen.back_requested.connect(self._back_to_browser)

        self.import_screen.imported.connect(self._after_import)
        self.import_screen.cancelled.connect(self._back_to_browser)
        self.card_browser.back_requested.connect(self._back_to_browser)
        self.stats_screen.back_requested.connect(self._back_to_browser)
        self.deck_settings_screen.back_requested.connect(self._back_to_browser)
        self.deck_settings_screen.deck_deleted.connect(self._back_to_browser)
        self.settings_screen.back_requested.connect(self._back_to_browser)

        self._back_to_browser()

    def _open_study_hub(self, deck_id: int) -> None:
        self._current_deck_id = deck_id
        self.study_hub.open_deck(deck_id)
        self.stack.setCurrentWidget(self.study_hub)

    def _back_to_hub(self) -> None:
        if self._current_deck_id is None:
            self._back_to_browser()
            return
        self._open_study_hub(self._current_deck_id)

    def _open_study_session(self, deck_id: int) -> None:
        self.study_session.start(deck_id)
        self.stack.setCurrentWidget(self.study_session)

    def _open_match(self, deck_id: int) -> None:
        self.match_screen.start(deck_id)
        self.stack.setCurrentWidget(self.match_screen)

    def _open_learn(self, deck_id: int) -> None:
        self.learn_screen.start(deck_id)
        self.stack.setCurrentWidget(self.learn_screen)

    def _open_test(self, deck_id: int) -> None:
        self.test_screen.start(deck_id)
        self.stack.setCurrentWidget(self.test_screen)

    def _open_history(self, deck_id: int) -> None:
        self.history_screen.open_deck(deck_id)
        self.stack.setCurrentWidget(self.history_screen)

    def _open_card_browser(self, deck_id: int) -> None:
        self.card_browser.open_deck(deck_id)
        self.stack.setCurrentWidget(self.card_browser)

    def _open_stats(self, deck_id: int) -> None:
        self.stats_screen.open_deck(deck_id)
        self.stack.setCurrentWidget(self.stats_screen)

    def _open_deck_settings(self, deck_id: int) -> None:
        self.deck_settings_screen.open_deck(deck_id)
        self.stack.setCurrentWidget(self.deck_settings_screen)

    def _open_settings(self) -> None:
        self.stack.setCurrentWidget(self.settings_screen)

    def _open_import(self) -> None:
        self.import_screen.refresh_decks()
        self.stack.setCurrentWidget(self.import_screen)

    def _after_import(self, deck_id: int) -> None:
        self._back_to_browser()

    def _create_deck(self) -> None:
        dialog = NewDeckDialog(parent=self)
        if dialog.exec():
            name, description = dialog.values()
            if not name:
                QMessageBox.warning(self, "Name required", "Give the deck a name first.")
                return
            with db_session() as conn:
                deck = deck_repository.create_deck(conn, name, description=description, source="manual")
            self._open_card_browser(deck.id)

    def _back_to_browser(self) -> None:
        self._current_deck_id = None
        self.deck_browser.refresh()
        self.stack.setCurrentWidget(self.deck_browser)
