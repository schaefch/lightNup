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
        self.parent.game_screen = GameScreen()
        self.parent.add_widget(self.parent.game_screen)
        self.parent.current = "menu"

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
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "game"
        self.add_widget(game.LevelWidget())

class GameScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_screen = GameScreen()
        self.transition = NoTransition()


class MainApp(App):
    def build(self):
        widget = GameScreenManager()
        widget.add_widget(MenuScreen())
        widget.add_widget(GameOverScreen())
        widget.add_widget(widget.game_screen)
        widget.current="menu"
        return widget


if __name__ == '__main__':
    MainApp().run()