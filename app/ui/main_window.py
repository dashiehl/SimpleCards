from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from app.config import APP_NAME
from app.db import deck_repository
from app.db.connection import db_session
from app.ui.widgets.card_browser import CardBrowser
from app.ui.widgets.deck_browser import DeckBrowser
from app.ui.widgets.deck_settings_screen import DeckSettingsScreen
from app.ui.widgets.import_screen import ImportScreen
from app.ui.widgets.new_deck_dialog import NewDeckDialog
from app.ui.widgets.stats_screen import StatsScreen
from app.ui.widgets.study_session import StudySession


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 750)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.deck_browser = DeckBrowser()
        self.study_session = StudySession()
        self.import_screen = ImportScreen()
        self.card_browser = CardBrowser()
        self.stats_screen = StatsScreen()
        self.deck_settings_screen = DeckSettingsScreen()

        for widget in (self.deck_browser, self.study_session, self.import_screen,
                       self.card_browser, self.stats_screen, self.deck_settings_screen):
            self.stack.addWidget(widget)

        self.deck_browser.study_requested.connect(self._open_study_session)
        self.deck_browser.browse_requested.connect(self._open_card_browser)
        self.deck_browser.stats_requested.connect(self._open_stats)
        self.deck_browser.settings_requested.connect(self._open_deck_settings)
        self.deck_browser.new_deck_requested.connect(self._create_deck)
        self.deck_browser.import_requested.connect(self._open_import)

        self.study_session.finished.connect(self._back_to_browser)
        self.import_screen.imported.connect(self._after_import)
        self.import_screen.cancelled.connect(self._back_to_browser)
        self.card_browser.back_requested.connect(self._back_to_browser)
        self.stats_screen.back_requested.connect(self._back_to_browser)
        self.deck_settings_screen.back_requested.connect(self._back_to_browser)
        self.deck_settings_screen.deck_deleted.connect(self._back_to_browser)

        self._back_to_browser()

    def _open_study_session(self, deck_id: int) -> None:
        self.study_session.start(deck_id)
        self.stack.setCurrentWidget(self.study_session)

    def _open_card_browser(self, deck_id: int) -> None:
        self.card_browser.open_deck(deck_id)
        self.stack.setCurrentWidget(self.card_browser)

    def _open_stats(self, deck_id: int) -> None:
        self.stats_screen.open_deck(deck_id)
        self.stack.setCurrentWidget(self.stats_screen)

    def _open_deck_settings(self, deck_id: int) -> None:
        self.deck_settings_screen.open_deck(deck_id)
        self.stack.setCurrentWidget(self.deck_settings_screen)

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
        self.deck_browser.refresh()
        self.stack.setCurrentWidget(self.deck_browser)
