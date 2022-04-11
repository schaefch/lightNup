from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.button import Button

import game


class GameOverScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "gameover"
        self.button = Button(text="Game Over!")
        self.add_widget(self.button)
        self.button.bind(on_press=self.to_menu)

    def to_menu(self, _):
        self.parent.remove_widget(self.parent.game_screen)
        self.parent.level = 1
        self.parent.game_screen = GameScreen(level=self.parent.level)
        self.parent.add_widget(self.parent.game_screen)
        self.parent.current = "menu"


class LevelUpScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "levelup"
        self.button = Button(text="Next Level!")
        self.add_widget(self.button)
        self.button.bind(on_press=self.to_next_level)

    def to_next_level(self, _):
        self.parent.remove_widget(self.parent.game_screen)
        self.parent.level += 1
        self.parent.game_screen = GameScreen(level=self.parent.level)
        self.parent.add_widget(self.parent.game_screen)
        self.parent.current = "game"


class MenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "menu"
        self.button = Button(text="Start!")
        self.add_widget(self.button)
        self.button.bind(on_press=self.to_game)

    def to_game(self, _):
        self.parent.current = "game"

class GameScreen(Screen):
    def __init__(self, level, **kw):
        super().__init__(**kw)
        self.name = "game"
        self.add_widget(game.LevelWidget(level=level))

class GameScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.level = 1
        self.game_screen = GameScreen(self.level)
        self.transition = NoTransition()


class MainApp(App):
    def build(self):
        widget = GameScreenManager()
        widget.add_widget(MenuScreen())
        widget.add_widget(GameOverScreen())
        widget.add_widget(LevelUpScreen())
        widget.add_widget(widget.game_screen)
        widget.current="menu"
        return widget


if __name__ == '__main__':
    MainApp().run()